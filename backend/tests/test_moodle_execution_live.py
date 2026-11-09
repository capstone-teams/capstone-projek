"""Integration test BE-16.2: eksekusi struktur course terhadap Moodle tim (opt-in).

Jalankan dengan ``MOODLE_LIVE_TESTS=1``. Setiap test membuat course uji baru di
Moodle, lalu menjalankan Structure Execution Service lewat orkestrator dengan
``MoodleIntegrationService`` sungguhan. Data aplikasi (workflow, course plan,
eksekusi) disimpan di database test seperti test lain.

Prasyarat: plugin ``local_capstonebridge`` minimal 0.6.0 terpasang dan
``local_capstonebridge_update_section`` sudah ditambahkan ke service web.
"""

import os
import uuid

import pytest
import pytest_asyncio

from src.config.settings import settings
from src.models.execution_operation import OperationStatus
from src.models.moodle_execution import ExecutionStatus
from src.services.execution.repository import ExecutionRepository
from src.services.execution.service import section_name
from src.services.moodle_client import MoodleClient
from src.services.moodle_exceptions import MoodleAPIError
from src.services.moodle_integration_service import MoodleIntegrationService
from src.services.rps.storage import LocalDocumentStorage
from tests.execution_fixtures import (
    UTS_WEEK,
    FixedSessionFactory,
    create_instructor,
    execute_structure,
    prepare_structure_workflow,
    retry_structure,
    semester_weeks,
)

pytestmark = pytest.mark.skipif(
    os.getenv("MOODLE_LIVE_TESTS") != "1",
    reason="Set MOODLE_LIVE_TESTS=1 untuk menjalankan test terhadap Moodle yang sedang menyala",
)


class FlakyWeekMoodle(MoodleIntegrationService):
    """Moodle tim, tetapi penyimpanan section minggu tertentu bisa digagalkan."""

    def __init__(self, client):
        super().__init__(client)
        self.fail_weeks: set[int] = set()
        self.saved_weeks: list[int | None] = []

    async def save_section(self, moodle_course_id, name, section_number=None, **kwargs):
        self.saved_weeks.append(section_number)
        if section_number in self.fail_weeks:
            raise MoodleAPIError(
                "Moodle menolak section (disimulasikan)",
                code="invalidparameter",
                wsfunction="local_capstonebridge_update_section",
            )
        return await super().save_section(moodle_course_id, name, section_number, **kwargs)


@pytest_asyncio.fixture
async def moodle():
    client = MoodleClient.from_settings(settings)
    try:
        yield FlakyWeekMoodle(client)
    finally:
        await client.aclose()


@pytest.fixture
def runner_env(monkeypatch, db_session):
    import src.services.workflow.orchestrator as orchestrator_module

    monkeypatch.setattr(orchestrator_module, "get_session_factory", lambda: FixedSessionFactory(db_session))


@pytest_asyncio.fixture
async def semester(db_session, tmp_path, moodle, runner_env):
    """Course Moodle baru dan workflow dengan course plan 16 minggu yang disetujui."""
    course = await moodle.create_course("Structure Execution Test", f"str-{uuid.uuid4().hex[:8]}", 1)
    owner_id = await create_instructor(db_session)
    workflow, plan = await prepare_structure_workflow(
        db_session,
        owner_id,
        LocalDocumentStorage(tmp_path),
        moodle_course_id=course.moodle_course_id,
        weeks=semester_weeks(),
    )
    return owner_id, workflow.id or "", plan, course.moodle_course_id


async def weekly_sections(moodle, course_id):
    contents = await moodle.get_course_contents(course_id)
    return [section for section in contents.sections if section.section_number > 0]


@pytest.mark.asyncio
async def test_sixteen_weeks_are_applied_once_and_a_rerun_adds_nothing(db_session, moodle, semester):
    owner_id, workflow_id, plan, course_id = semester

    first_id = await execute_structure(db_session, moodle, workflow_id, owner_id)
    first = await ExecutionRepository(db_session).get(first_id)
    after_first = await weekly_sections(moodle, course_id)

    second_id = await execute_structure(db_session, moodle, workflow_id, owner_id)
    second = await ExecutionRepository(db_session).get(second_id)
    after_second = await weekly_sections(moodle, course_id)

    assert first.status is ExecutionStatus.SUCCESS, first.error_message
    assert first.readback["matches"] is True
    assert [(s.section_number, s.name) for s in after_first] == [
        (week.week_number, section_name(week)) for week in plan.weeks
    ]
    assert "Topik 1.1" in after_first[0].summary and "Sub-CPMK-1" in after_first[0].summary
    assert "Ujian Tengah Semester (UTS)" in after_first[UTS_WEEK - 1].summary
    assert [op.moodle_object_id for op in first.operations] == [str(s.moodle_section_id) for s in after_first]

    assert second.status is ExecutionStatus.SUCCESS, second.error_message
    assert second.readback["matches"] is True
    assert [s.moodle_section_id for s in after_second] == [s.moodle_section_id for s in after_first]
    assert len(after_second) == 16


@pytest.mark.asyncio
async def test_failed_week_is_retried_without_repeating_the_successful_ones(db_session, moodle, semester):
    owner_id, workflow_id, _, course_id = semester
    moodle.fail_weeks = {5}

    execution_id = await execute_structure(db_session, moodle, workflow_id, owner_id)
    failed = await ExecutionRepository(db_session).get(execution_id)

    moodle.fail_weeks.clear()
    moodle.saved_weeks.clear()
    await retry_structure(db_session, moodle, workflow_id, owner_id, execution_id)
    retried = await ExecutionRepository(db_session).get(execution_id)
    sections = await weekly_sections(moodle, course_id)

    assert failed.status is ExecutionStatus.FAILED
    assert (failed.summary.success, failed.summary.failed) == (15, 1)
    # Section minggu 5 tetap disisipkan (kosong) agar minggu 6 dst. tidak bergeser.
    assert failed.readback["missing_weeks"] + failed.readback["mismatched_weeks"] == [5]
    assert [op.week_number for op in failed.operations if op.status is OperationStatus.FAILED] == [5]
    assert moodle.saved_weeks == [5]
    assert retried.status is ExecutionStatus.SUCCESS, retried.error_message
    assert retried.readback["matches"] is True
    assert all(op.status is OperationStatus.SUCCESS for op in retried.operations)
    assert [s.section_number for s in sections] == list(range(1, 17))