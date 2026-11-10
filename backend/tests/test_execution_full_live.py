"""Integration test BE-21.1: eksekusi ``FULL`` terhadap Moodle tim (opt-in).

Jalankan dengan ``MOODLE_LIVE_TESTS=1``. Test membuat course uji baru di Moodle,
lalu menerapkan section mingguan beserta keempat jenis konten ``APPROVED``
(learning material, learning resource, assignment, quiz) melalui orkestrator
dengan ``MoodleIntegrationService`` sungguhan.

Yang dibuktikan (acceptance criteria BE-21.1):

- satu minggu contoh berisi page, url, assign, dan quiz pada section yang benar;
- eksekusi ulang tidak membuat activity baru;
- setelah satu konten digenerate ulang dan disetujui, eksekusi berikutnya
  memperbarui activity yang sama, bukan membuat duplikat.

Prasyarat: plugin ``local_capstonebridge`` versi yang mendukung create/update
page, url, assign, dan quiz sudah terpasang pada instance Moodle tim.
"""

import os
import uuid

import pytest
import pytest_asyncio

from src.config.settings import settings
from src.models.execution_operation import OperationStatus
from src.models.moodle_execution import ExecutionStatus
from src.services.content.domain import ContentKind
from src.services.execution.repository import ExecutionRepository
from src.services.moodle_client import MoodleClient
from src.services.moodle_integration_service import MoodleIntegrationService
from src.services.rps.storage import LocalDocumentStorage
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

MODULE_BY_KIND = {
    ContentKind.LEARNING_MATERIAL: "page",
    ContentKind.RESOURCE: "url",
    ContentKind.ASSIGNMENT: "assign",
    ContentKind.QUIZ: "quiz",
}


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
async def scenario(db_session, tmp_path, moodle, runner_env):
    """Course Moodle baru, workflow, dan konten APPROVED minggu 1."""
    course = await moodle.create_course(
        "Full Execution Test", f"full-{uuid.uuid4().hex[:8]}", 1
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
        await approve_content(
            db_session, workflow.id or "", plan, kind, 1, data
        )
    return owner_id, workflow.id or "", plan, course.moodle_course_id


async def week_modules(moodle, course_id: int, week: int):
    contents = await moodle.get_course_contents(course_id)
    section = next(
        item for item in contents.sections if item.section_number == week
    )
    return section, {module.modname: module for module in section.modules}


@pytest.mark.asyncio
async def test_week_contents_are_applied_once_and_regeneration_updates_the_same_activity(
    db_session, moodle, scenario
):
    owner_id, workflow_id, plan, course_id = scenario

    first_id = await execute_full(db_session, moodle, workflow_id, owner_id)
    first = await ExecutionRepository(db_session).get(first_id)
    _, modules = await week_modules(moodle, course_id, 1)

    assert first.status is ExecutionStatus.SUCCESS, first.error_message
    assert set(MODULE_BY_KIND.values()) <= set(modules)
    assert sorted(module.name for module in modules.values()) == sorted(
        f"{kind.value} minggu 1" for kind in MODULE_BY_KIND
    )
    page = modules["page"]
    assert "Pengantar" in (page.content or "")
    assert '<a href="https://developer.mozilla.org">MDN</a>' in (page.content or "")
    assert 'href="javascript:' not in (page.content or "")
    content_operations = [
        operation
        for operation in first.operations
        if operation.operation_type.value != "SECTION"
        and operation.week_number == 1
    ]
    assert all(
        operation.status is OperationStatus.SUCCESS
        for operation in content_operations
    )
    assert all(operation.moodle_object_id for operation in content_operations)

    second_id = await execute_full(db_session, moodle, workflow_id, owner_id)
    second = await ExecutionRepository(db_session).get(second_id)
    _, rerun_modules = await week_modules(moodle, course_id, 1)

    assert second.status is ExecutionStatus.SUCCESS, second.error_message
    assert {
        name: module.moodle_module_id for name, module in modules.items()
    } == {
        name: module.moodle_module_id for name, module in rerun_modules.items()
    }

    regenerated = await approve_content(
        db_session,
        workflow_id,
        plan,
        ContentKind.LEARNING_MATERIAL,
        1,
        {
            **material_data(1),
            "sections": [{"heading": "Revisi", "body_markdown": "Isi baru."}],
        },
    )
    assert regenerated.version == 2

    third_id = await execute_full(db_session, moodle, workflow_id, owner_id)
    third = await ExecutionRepository(db_session).get(third_id)
    third_section, updated_modules = await week_modules(moodle, course_id, 1)

    assert third.status is ExecutionStatus.SUCCESS, third.error_message
    assert updated_modules["page"].moodle_module_id == modules["page"].moodle_module_id
    assert "Revisi" in (updated_modules["page"].content or "")
    # Jenis lain tidak berubah: hanya satu activity per jenis.
    assert len(third_section.modules) == len(MODULE_BY_KIND)
