"""Integration test BE-21.2: Moodle verification terhadap Moodle tim (opt-in).

Jalankan dengan ``MOODLE_LIVE_TESTS=1``. Test membuat course baru, mengeksekusi
course plan 2 minggu beserta keempat jenis konten ``APPROVED`` pada minggu 1
(BE-21.1), lalu memverifikasinya:

- course hasil eksekusi FULL terverifikasi ``PASS``;
- activity yang dihapus manual dari Moodle terdeteksi, dibuat ulang, dan
  verifikasi berikutnya ``PASS`` tanpa perbaikan.

Prasyarat: plugin ``local_capstonebridge`` 0.6.0 dan, khusus test ini,
``core_course_delete_modules`` pada service web (dipakai untuk meniru activity
yang dihapus manual; aplikasi sendiri tidak pernah menghapus activity).
"""

import os
import uuid

import pytest
import pytest_asyncio

from src.config.settings import settings
from src.models.execution_operation import OperationType
from src.models.verification import VerificationStatus
from src.services.content.domain import ContentKind
from src.services.execution.repository import ExecutionRepository
from src.services.moodle_client import MoodleClient
from src.services.moodle_exceptions import MoodlePermissionError
from src.services.moodle_integration_service import MoodleIntegrationService
from src.services.rps.storage import LocalDocumentStorage
from src.services.verification.service import VerificationService
from tests.execution_fixtures import (
    FixedSessionFactory,
    approve_content,
    assignment_data,
    create_instructor,
    enable_all_activities,
    execute_full,
    material_data,
    prepare_structure_workflow,
    quiz_data,
    resource_data,
    semester_weeks,
)

pytestmark = pytest.mark.skipif(
    os.getenv("MOODLE_LIVE_TESTS") != "1",
    reason="Set MOODLE_LIVE_TESTS=1 untuk menjalankan test terhadap Moodle yang sedang menyala",
)


@pytest_asyncio.fixture
async def moodle():
    client = MoodleClient.from_settings(settings)
    try:
        yield MoodleIntegrationService(client)
    finally:
        await client.aclose()


@pytest.fixture
def runner_env(monkeypatch, db_session):
    import src.services.workflow.orchestrator as orchestrator_module

    monkeypatch.setattr(
        orchestrator_module,
        "get_session_factory",
        lambda: FixedSessionFactory(db_session),
    )


@pytest_asyncio.fixture
async def executed(db_session, tmp_path, moodle, runner_env):
    """Course baru yang sudah dieksekusi FULL: 2 section, 4 activity di minggu 1."""
    course = await moodle.create_course(
        "Verification Test", f"ver-{uuid.uuid4().hex[:8]}", 1
    )
    owner_id = await create_instructor(db_session)
    workflow, plan = await prepare_structure_workflow(
        db_session,
        owner_id,
        LocalDocumentStorage(tmp_path),
        moodle_course_id=course.moodle_course_id,
        weeks=semester_weeks(2),
    )
    await enable_all_activities(db_session, owner_id)
    for kind, data in (
        (ContentKind.LEARNING_MATERIAL, material_data(1)),
        (ContentKind.RESOURCE, resource_data(1)),
        (ContentKind.ASSIGNMENT, assignment_data(1)),
        (ContentKind.QUIZ, quiz_data(1)),
    ):
        await approve_content(db_session, workflow.id or "", plan, kind, 1, data)
    execution_id = await execute_full(db_session, moodle, workflow.id or "", owner_id)
    return owner_id, workflow.id or "", execution_id, course.moodle_course_id


async def week_one_modules(moodle, course_id):
    contents = await moodle.get_course_contents(course_id)
    section = next(item for item in contents.sections if item.section_number == 1)
    return {module.modname: module for module in section.modules}


@pytest.mark.asyncio
async def test_full_execution_is_verified_and_a_deleted_activity_is_recreated(
    db_session, moodle, executed
):
    owner_id, workflow_id, execution_id, course_id = executed
    verifications = VerificationService.from_session(db_session, moodle=moodle)

    initial = await verifications.verify(workflow_id=workflow_id, owner_id=owner_id)
    before = await week_one_modules(moodle, course_id)
    try:
        await moodle.client.call(
            "core_course_delete_modules", {"cmids": [before["page"].moodle_module_id]}
        )
    except MoodlePermissionError:
        pytest.skip(
            "Tambahkan core_course_delete_modules ke service untuk test ini (guide bagian 7.1, function 29)"
        )
    repaired = await verifications.verify(workflow_id=workflow_id, owner_id=owner_id)
    after = await week_one_modules(moodle, course_id)
    final = await verifications.verify(workflow_id=workflow_id, owner_id=owner_id)

    execution = await ExecutionRepository(db_session).get(execution_id)
    page_operation = next(
        op
        for op in execution.operations
        if op.operation_type is OperationType.LEARNING_MATERIAL
    )
    assert initial.status is VerificationStatus.PASS, [
        item.to_dict() for item in initial.discrepancies
    ]
    assert initial.summary["found_activities"] == 4
    assert repaired.status is VerificationStatus.PASS, [
        item.to_dict() for item in repaired.discrepancies
    ]
    assert [(item.type.value, item.target) for item in repaired.repaired] == [
        ("MISSING", "LEARNING_MATERIAL")
    ]
    assert repaired.repair_count == 1
    assert set(after) == {"page", "url", "assign", "quiz"}
    assert after["page"].moodle_module_id != before["page"].moodle_module_id
    assert page_operation.moodle_object_id == str(after["page"].moodle_module_id)
    assert final.status is VerificationStatus.PASS
    assert final.repair_count == 0