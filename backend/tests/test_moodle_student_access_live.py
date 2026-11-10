"""Integration test BE-16.3: student access pada course hasil eksekusi (opt-in).

Jalankan dengan ``MOODLE_LIVE_TESTS=1`` dan akun uji dari
``scripts.setup_moodle_test_accounts``:

* ``MOODLE_STUDENT_USERNAME`` / ``MOODLE_STUDENT_PASSWORD``: mahasiswa yang didaftarkan;
* ``MOODLE_STUDENT2_USERNAME`` / ``MOODLE_STUDENT2_PASSWORD``: mahasiswa yang **tidak** didaftarkan.

Setiap test membuat course baru, mengeksekusi course plan 16 minggu ke course
itu (BE-16.2), lalu membuktikan akses mahasiswa dengan token milik mahasiswa.
"""

import os
import uuid

import pytest
import pytest_asyncio

from src.config.settings import settings
from src.services.execution.service import section_name
from src.services.moodle_client import MoodleClient
from src.services.moodle_integration_service import MoodleIntegrationService
from src.services.moodle_student_access import MoodleStudentAccessService
from src.services.rps.storage import LocalDocumentStorage
from tests.execution_fixtures import (
    FixedSessionFactory,
    create_instructor,
    execute_structure,
    prepare_structure_workflow,
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
async def executed_course(db_session, tmp_path, moodle, runner_env):
    """Course Moodle baru yang strukturnya sudah dieksekusi dari course plan 16 minggu."""
    course = await moodle.create_course(
        "Student Access Test", f"stu-{uuid.uuid4().hex[:8]}", 1
    )
    owner_id = await create_instructor(db_session)
    workflow, plan = await prepare_structure_workflow(
        db_session,
        owner_id,
        LocalDocumentStorage(tmp_path),
        moodle_course_id=course.moodle_course_id,
        weeks=semester_weeks(),
    )
    await execute_structure(db_session, moodle, workflow.id or "", owner_id)
    return course.moodle_course_id, plan


@pytest.mark.asyncio
async def test_enrolled_student_sees_every_week_and_an_unenrolled_student_is_rejected(
    access, executed_course
):
    course_id, plan = executed_course

    await access.enrol_students(course_id, [STUDENT[0]])
    report = await access.verify(
        course_id, enrolled=STUDENT, not_enrolled=OTHER_STUDENT
    )

    assert report.visibility.course_visible is True
    assert report.visibility.hidden_sections == ()
    assert report.enrolled.weekly_sections == tuple(
        (week.week_number, section_name(week)) for week in plan.weeks
    )
    assert report.not_enrolled.can_open is False
    assert report.not_enrolled.error_code in {
        "requireloginerror",
        "errorcoursecontextnotvalid",
    }
    assert report.ok is True, report.to_dict()


@pytest.mark.asyncio
async def test_hidden_week_is_detected_and_shown_again(moodle, access, executed_course):
    course_id, _ = executed_course
    await access.enrol_students(course_id, [STUDENT[0]])
    third = next(
        s
        for s in (await moodle.get_course_contents(course_id)).sections
        if s.section_number == 3
    )
    await moodle.set_section_visibility(course_id, [third.moodle_section_id], False)

    hidden = await access.verify(
        course_id, enrolled=STUDENT, not_enrolled=OTHER_STUDENT
    )
    await access.ensure_visible(course_id)
    shown = await access.verify(course_id, enrolled=STUDENT, not_enrolled=OTHER_STUDENT)

    assert hidden.visibility.hidden_sections == (3,)
    assert 3 not in [number for number, _ in hidden.enrolled.weekly_sections]
    assert hidden.ok is False
    assert shown.visibility.hidden_sections == ()
    assert len(shown.enrolled.weekly_sections) == 16
    assert shown.ok is True, shown.to_dict()