"""Integration test BE-21.3: mahasiswa membuka activity hasil eksekusi FULL (opt-in).

Jalankan dengan ``MOODLE_LIVE_TESTS=1`` dan akun uji dari
``scripts.setup_moodle_test_accounts``:

* ``MOODLE_STUDENT_USERNAME`` / ``MOODLE_STUDENT_PASSWORD``: mahasiswa yang didaftarkan;
* ``MOODLE_STUDENT2_USERNAME`` / ``MOODLE_STUDENT2_PASSWORD``: mahasiswa yang **tidak** didaftarkan.

Setiap test membuat course baru, mengeksekusi course plan 2 minggu beserta
keempat jenis konten ``APPROVED`` pada minggu 1 (BE-21.1), lalu membuktikan akses
mahasiswa dengan token milik mahasiswa: page dan url dibuka, assignment dibuka,
dan attempt quiz benar-benar dimulai lalu diselesaikan.
"""

import os
import uuid

import pytest
import pytest_asyncio

from src.config.settings import settings
from src.services.content.domain import ContentKind
from src.services.moodle_client import MoodleClient
from src.services.moodle_integration_service import MoodleIntegrationService
from src.services.moodle_student_access import MoodleStudentAccessService
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

STUDENT = (os.getenv("MOODLE_STUDENT_USERNAME"), os.getenv("MOODLE_STUDENT_PASSWORD"))
OTHER_STUDENT = (
    os.getenv("MOODLE_STUDENT2_USERNAME"),
    os.getenv("MOODLE_STUDENT2_PASSWORD"),
)

pytestmark = [
    pytest.mark.skipif(
        os.getenv("MOODLE_LIVE_TESTS") != "1",
        reason="Set MOODLE_LIVE_TESTS=1 untuk menjalankan test terhadap Moodle yang sedang menyala",
    ),
    pytest.mark.skipif(
        not (all(STUDENT) and all(OTHER_STUDENT)),
        reason="Isi MOODLE_STUDENT_* dan MOODLE_STUDENT2_* (akun dari scripts.setup_moodle_test_accounts)",
    ),
]

ACTIVITY_TYPES = {"page", "url", "assign", "quiz"}


@pytest_asyncio.fixture
async def moodle():
    client = MoodleClient.from_settings(settings)
    try:
        yield MoodleIntegrationService(client)
    finally:
        await client.aclose()


@pytest.fixture
def access(moodle):
    return MoodleStudentAccessService.from_settings(moodle, settings)


@pytest.fixture
def runner_env(monkeypatch, db_session):
    import src.services.workflow.orchestrator as orchestrator_module

    monkeypatch.setattr(
        orchestrator_module,
        "get_session_factory",
        lambda: FixedSessionFactory(db_session),
    )


@pytest_asyncio.fixture
async def executed_course(db_session, tmp_path, moodle, access, runner_env):
    """Course baru hasil eksekusi FULL dengan mahasiswa uji terdaftar."""
    course = await moodle.create_course(
        "Student Activity Test", f"act-{uuid.uuid4().hex[:8]}", 1
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
    await execute_full(db_session, moodle, workflow.id or "", owner_id)
    await access.enrol_students(course.moodle_course_id, [STUDENT[0]])
    return course.moodle_course_id


@pytest.mark.asyncio
async def test_enrolled_student_opens_every_activity_and_others_are_rejected(
    access, executed_course
):
    report = await access.verify(
        executed_course, enrolled=STUDENT, not_enrolled=OTHER_STUDENT, start_quiz=True
    )

    opened = {item.modname: item for item in report.enrolled.activities}
    assert set(opened) == ACTIVITY_TYPES
    assert all(item.opened for item in opened.values()), report.to_dict()
    assert opened["quiz"].attempt_started is True, report.to_dict()
    assert report.visibility.hidden_activities == ()
    assert len(report.not_enrolled.activities) == 4
    assert not any(item.opened for item in report.not_enrolled.activities)
    assert report.ok is True, report.to_dict()


@pytest.mark.asyncio
async def test_hidden_activity_is_detected_and_shown_again(
    moodle, access, executed_course
):
    before = await access.check_visibility(executed_course)
    assignment = next(item for item in before.activities if item.modname == "assign")
    await moodle.set_module_visibility(
        executed_course, [assignment.moodle_module_id], False
    )

    hidden = await access.verify(
        executed_course, enrolled=STUDENT, not_enrolled=OTHER_STUDENT
    )
    await access.ensure_visible(executed_course)
    shown = await access.verify(
        executed_course, enrolled=STUDENT, not_enrolled=OTHER_STUDENT
    )

    hidden_assignment = next(
        item for item in hidden.enrolled.activities if item.modname == "assign"
    )
    assert hidden.visibility.hidden_activities == (assignment.moodle_module_id,)
    assert hidden_assignment.opened is False
    assert hidden.ok is False
    assert shown.visibility.hidden_activities == ()
    assert shown.ok is True, shown.to_dict()