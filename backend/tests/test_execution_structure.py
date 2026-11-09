"""Test Structure Execution Service (BE-16.2) melalui Moodle Integration Layer.

Berbeda dari ``test_execution_orchestrator.py`` (BE-17.1) yang mengganti
``MoodleIntegrationService`` dengan objek palsu, test ini menjalankan
``MoodleIntegrationService`` dan ``MoodleClient`` sungguhan terhadap Moodle
tiruan berbasis HTTP (``tests.moodle_fakes``), sehingga payload web service
yang dikirim ikut diuji. Acceptance criteria BE-16.2 yang dibuktikan:

- course plan 16 minggu menghasilkan 16 section dengan nama, ringkasan, dan
  urutan yang benar (minggu UTS/UAS diberi penanda);
- eksekusi kedua tanpa perubahan course plan tidak menambah section dan
  memperbarui section yang tercatat pada tabel mapping BE-04.3;
- operasi gagal dapat diulang tanpa mengulang operasi yang berhasil;
- hasil read-back sesuai course plan, dan ketidaksesuaian menggagalkan eksekusi.

Integration test terhadap Moodle tim ada di ``test_moodle_execution_live.py``.
"""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from src.models.execution_operation import OperationStatus
from src.models.moodle_execution import ExecutionStatus
from src.models.workflow import WorkflowStatus
from src.models.workflow_event import EventType
from src.services.course_plan.domain import CoursePlanWeekRecord
from src.services.execution.repository import ExecutionRepository
from src.services.execution.service import SECTION_ENTITY_TYPE, section_name, section_summary
from src.services.moodle_client import MoodleClient
from src.services.moodle_integration_service import MoodleIntegrationService
from src.services.moodle_mapping import MoodleMapping
from src.services.moodle_mapping_sql import SqlMoodleMappingRepository
from src.services.rps.storage import LocalDocumentStorage
from src.services.workflow.service import WorkflowService
from tests.execution_fixtures import (
    UAS_WEEK,
    UTS_WEEK,
    FixedSessionFactory,
    create_instructor,
    execute_structure,
    prepare_structure_workflow,
    retry_structure,
    semester_weeks,
)
from tests.moodle_fakes import BASE_URL, TOKEN, FakeMoodle, moodle_exception

COURSE_ID = 3
UPDATE_SECTION = "local_capstonebridge_update_section"
ADD_SECTION = "core_courseformat_update_course"


class CourseMoodle(FakeMoodle):
    """Moodle tiruan dengan course kosong (hanya section General) yang dapat gagal per minggu."""

    def __init__(self) -> None:
        super().__init__()
        self.courses[COURSE_ID] = {
            "id": COURSE_ID,
            "fullname": "Basis Data",
            "shortname": "IF123",
            "format": "topics",
            "visible": 1,
            "categoryid": 1,
            "summary": "",
        }
        self.sections[COURSE_ID] = [
            {"id": 300, "section": 0, "name": "General", "summary": "", "visible": 1, "modules": []}
        ]
        self.fail_weeks: set[int] = set()
        #: Nama yang disimpan Moodle berbeda dari yang dikirim (untuk menguji read-back).
        self.rename_weeks: dict[int, str] = {}

    def _dispatch(self, wsfunction, params):
        if wsfunction == UPDATE_SECTION:
            number = self.section_number(int(params["sectionid"]))
            if number in self.fail_weeks:
                return moodle_exception("invalidparameter", "Invalid parameter value detected",
                                        "invalid_parameter_exception")
            result = super()._dispatch(wsfunction, params)
            if number in self.rename_weeks:
                self.section(number)["name"] = self.rename_weeks[number]
            return result
        return super()._dispatch(wsfunction, params)

    def section(self, number: int) -> dict:
        return next(item for item in self.sections[COURSE_ID] if item["section"] == number)

    def section_number(self, section_id: int) -> int | None:
        return next((item["section"] for item in self.sections[COURSE_ID] if item["id"] == section_id), None)

    def weekly(self) -> list[dict]:
        return [item for item in self.sections[COURSE_ID] if item["section"] > 0]

    def updated_weeks(self) -> list[int | None]:
        return [self.section_number(int(params["sectionid"])) for params in self.called(UPDATE_SECTION)]


@pytest.fixture
def moodle_fake() -> CourseMoodle:
    return CourseMoodle()


@pytest_asyncio.fixture
async def moodle(moodle_fake):
    client = MoodleClient(BASE_URL, TOKEN, transport=httpx.MockTransport(moodle_fake.handler))
    try:
        yield MoodleIntegrationService(client)
    finally:
        await client.aclose()


@pytest.fixture
def runner_env(monkeypatch, db_session):
    import src.services.workflow.orchestrator as orchestrator_module

    monkeypatch.setattr(orchestrator_module, "get_session_factory", lambda: FixedSessionFactory(db_session))


@pytest_asyncio.fixture
async def semester(db_session, tmp_path, runner_env):
    owner_id = await create_instructor(db_session)
    workflow, plan = await prepare_structure_workflow(
        db_session, owner_id, LocalDocumentStorage(tmp_path), moodle_course_id=COURSE_ID, weeks=semester_weeks()
    )
    return owner_id, workflow.id or "", plan


async def _load(session, execution_id):
    return await ExecutionRepository(session).get(execution_id)


# --- Nama dan ringkasan section ---------------------------------------------


@pytest.mark.parametrize(
    ("week", "expected"),
    [
        (CoursePlanWeekRecord(week_number=3, title="Relasi  Tabel"), "Minggu 3 - Relasi Tabel"),
        (CoursePlanWeekRecord(week_number=8, title="Ujian Tengah Semester", week_type="uts"),
         "Minggu 8 - Ujian Tengah Semester (UTS)"),
        (CoursePlanWeekRecord(week_number=8, title="UTS", week_type="uts"), "Minggu 8 - UTS"),
        (CoursePlanWeekRecord(week_number=16, title="Ujian Akhir Semester", week_type="uas"),
         "Minggu 16 - Ujian Akhir Semester (UAS)"),
        (CoursePlanWeekRecord(week_number=4, title="Kuis 1", week_type="kuis"), "Minggu 4 - Kuis 1"),
    ],
)
def test_section_name_follows_the_week_and_marks_exam_weeks(week, expected):
    assert section_name(week) == expected


def test_long_section_name_is_truncated_without_losing_the_exam_marker():
    name = section_name(CoursePlanWeekRecord(week_number=8, title="x" * 400, week_type="uts"))

    assert len(name) == 255
    assert name.startswith("Minggu 8 - xxx")
    assert name.endswith("… (UTS)")


def test_section_summary_lists_objectives_topics_and_sub_cpmk():
    week = CoursePlanWeekRecord(
        week_number=2,
        title="Normalisasi",
        objectives=("Menjelaskan 1NF & 2NF", " "),
        topics=("Dependensi <fungsional>",),
        learning_outcomes=("Sub-CPMK-1.1", "Sub-CPMK-1.2"),
    )

    assert section_summary(week) == (
        "<p><strong>Tujuan Pembelajaran</strong></p><ul><li>Menjelaskan 1NF &amp; 2NF</li></ul>"
        "<p><strong>Topik</strong></p><ul><li>Dependensi &lt;fungsional&gt;</li></ul>"
        "<p><strong>Sub-CPMK:</strong> Sub-CPMK-1.1, Sub-CPMK-1.2</p>"
    )


def test_exam_week_summary_starts_with_the_exam_label():
    uas = CoursePlanWeekRecord(week_number=16, title="Ujian Akhir Semester", week_type="uas")

    assert section_summary(uas) == "<p><strong>Ujian Akhir Semester (UAS)</strong></p>"
    assert section_summary(CoursePlanWeekRecord(week_number=1, title="Kosong")) == ""


# --- Eksekusi lewat Moodle Integration Layer ---------------------------------


@pytest.mark.asyncio
async def test_sixteen_week_plan_creates_sixteen_ordered_named_sections(db_session, moodle, moodle_fake, semester):
    owner_id, workflow_id, plan = semester

    execution_id = await execute_structure(db_session, moodle, workflow_id, owner_id)

    stored = await _load(db_session, execution_id)
    weekly = moodle_fake.weekly()
    assert stored.status is ExecutionStatus.SUCCESS
    assert stored.summary.total == stored.summary.success == 16
    assert [(item["section"], item["name"]) for item in weekly] == [
        (week.week_number, section_name(week)) for week in plan.weeks
    ]
    assert weekly[UTS_WEEK - 1]["name"] == "Minggu 8 - Ujian Tengah Semester (UTS)"
    assert weekly[UAS_WEEK - 1]["name"] == "Minggu 16 - Ujian Akhir Semester (UAS)"
    assert "Topik 1.1" in weekly[0]["summary"] and "Sub-CPMK-1" in weekly[0]["summary"]
    assert weekly[UTS_WEEK - 1]["summary"].startswith("<p><strong>Ujian Tengah Semester (UTS)")
    assert len(moodle_fake.called(ADD_SECTION)) == 16
    assert moodle_fake.called("core_update_inplace_editable") == []
    assert stored.readback == {
        "checked": True,
        "matches": True,
        "expected_sections": 16,
        "actual_sections": 16,
        "ordered": True,
        "missing_weeks": [],
        "mismatched_weeks": [],
    }
    assert [op.moodle_object_id for op in stored.operations] == [str(item["id"]) for item in weekly]

    mappings = SqlMoodleMappingRepository(db_session)
    assert [await mappings.get_moodle_id(SECTION_ENTITY_TYPE, week.id) for week in plan.weeks] == [
        item["id"] for item in weekly
    ]
    workflow = await WorkflowService.from_session(db_session).get_workflow(workflow_id=workflow_id, owner_id=owner_id)
    assert workflow.status is WorkflowStatus.WAITING_FOR_REVIEW
    events = await WorkflowService.from_session(db_session).list_events(workflow_id=workflow_id, owner_id=owner_id)
    operation_events = [event for event in events if event.event_type is EventType.OPERASI_MOODLE]
    assert len(operation_events) == 16


@pytest.mark.asyncio
async def test_second_execution_updates_the_mapped_sections_without_adding_any(
    db_session, moodle, moodle_fake, semester
):
    owner_id, workflow_id, _ = semester
    first = await execute_structure(db_session, moodle, workflow_id, owner_id)
    section_ids = [item["id"] for item in moodle_fake.weekly()]
    moodle_fake.calls.clear()

    second = await execute_structure(db_session, moodle, workflow_id, owner_id)

    stored = await _load(db_session, second)
    assert second != first
    assert stored.status is ExecutionStatus.SUCCESS
    assert [item["id"] for item in moodle_fake.weekly()] == section_ids
    assert moodle_fake.called(ADD_SECTION) == []
    assert [int(params["sectionid"]) for params in moodle_fake.called(UPDATE_SECTION)] == section_ids
    assert stored.readback["matches"] is True


@pytest.mark.asyncio
async def test_mapped_section_is_updated_by_id_and_a_stale_mapping_falls_back_to_the_week_number(
    db_session, moodle, moodle_fake, semester
):
    owner_id, workflow_id, plan = semester
    # Section minggu 1 sudah ada dan tercatat; mapping minggu 2 menunjuk section yang sudah dihapus.
    moodle_fake.sections[COURSE_ID].append(
        {"id": 350, "section": 1, "name": "Topik lama", "summary": "", "visible": 1, "modules": []}
    )
    mappings = SqlMoodleMappingRepository(db_session)
    await mappings.save(MoodleMapping(entity_type=SECTION_ENTITY_TYPE, internal_id=plan.weeks[0].id, moodle_id=350))
    await mappings.save(MoodleMapping(entity_type=SECTION_ENTITY_TYPE, internal_id=plan.weeks[1].id, moodle_id=999))

    execution_id = await execute_structure(db_session, moodle, workflow_id, owner_id)

    stored = await _load(db_session, execution_id)
    assert moodle_fake.section(1)["id"] == 350
    assert moodle_fake.section(1)["name"] == section_name(plan.weeks[0])
    assert len(moodle_fake.weekly()) == 16
    assert len(moodle_fake.called(ADD_SECTION)) == 15
    assert stored.operations[0].moodle_object_id == "350"
    assert stored.status is ExecutionStatus.SUCCESS


@pytest.mark.asyncio
async def test_failed_week_does_not_stop_the_others_and_retry_reruns_only_that_week(
    db_session, moodle, moodle_fake, semester
):
    owner_id, workflow_id, _ = semester
    moodle_fake.fail_weeks = {5}

    execution_id = await execute_structure(db_session, moodle, workflow_id, owner_id)

    failed = await _load(db_session, execution_id)
    week_five = next(op for op in failed.operations if op.week_number == 5)
    assert failed.status is ExecutionStatus.FAILED
    assert (failed.summary.success, failed.summary.failed) == (15, 1)
    assert week_five.status is OperationStatus.FAILED and week_five.error_message
    assert failed.readback["mismatched_weeks"] == [5]
    workflow = await WorkflowService.from_session(db_session).get_workflow(workflow_id=workflow_id, owner_id=owner_id)
    assert workflow.status is WorkflowStatus.FAILED

    moodle_fake.fail_weeks.clear()
    moodle_fake.calls.clear()
    await retry_structure(db_session, moodle, workflow_id, owner_id, execution_id)

    retried = await _load(db_session, execution_id)
    week_five = next(op for op in retried.operations if op.week_number == 5)
    assert retried.status is ExecutionStatus.SUCCESS
    assert (retried.summary.success, retried.summary.failed) == (16, 0)
    assert moodle_fake.updated_weeks() == [5]
    assert moodle_fake.called(ADD_SECTION) == []
    assert week_five.retry_count == 1
    assert all(op.retry_count == 0 for op in retried.operations if op.week_number != 5)
    assert retried.readback["matches"] is True
    assert len(moodle_fake.weekly()) == 16


@pytest.mark.asyncio
async def test_read_back_mismatch_fails_the_execution(db_session, moodle, moodle_fake, semester):
    owner_id, workflow_id, _ = semester
    moodle_fake.rename_weeks = {3: "Diubah manual"}

    execution_id = await execute_structure(db_session, moodle, workflow_id, owner_id)

    stored = await _load(db_session, execution_id)
    assert stored.summary.failed == 0
    assert stored.status is ExecutionStatus.FAILED
    assert stored.error_message == "Hasil read-back tidak sesuai course plan."
    assert stored.readback["matches"] is False
    assert stored.readback["mismatched_weeks"] == [3]