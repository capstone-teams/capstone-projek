"""Test tahap eksekusi Moodle pada orkestrator (BE-17.1).

Membuktikan acceptance criteria BE-17.1 tanpa Moodle sungguhan:

- setiap prasyarat yang tidak terpenuhi menolak eksekusi dengan kode alasan
  ``PLAN_NOT_APPROVED``, ``MOODLE_TARGET_NOT_SET``, ``MOODLE_UNAVAILABLE``,
  atau ``EXECUTION_IN_PROGRESS``;
- eksekusi dengan prasyarat terpenuhi membuat satu operasi ``SECTION`` per
  minggu, berakhir ``SUCCESS``, dan workflow kembali ke ``WAITING_FOR_REVIEW``
  (DL-012);
- kegagalan satu operasi tidak menghentikan minggu lain, menghasilkan workflow
  ``FAILED``, dan retry hanya mengulang operasi gagal pada eksekusi yang sama;
- event ``OPERASI_MOODLE`` tercatat per operasi dan transisi tahap tercatat
  sebagai ``PERUBAHAN_TAHAP``;
- eksekusi kedua memperbarui section yang sama (idempotent), bukan menambah.

Moodle diganti objek palsu; runner dijalankan langsung dengan session factory
test — pola yang sama dengan ``test_workflow_orchestrator.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
import pytest_asyncio
import shortuuid

from src.models.course_plan import CoursePlanStatus
from src.models.execution_operation import OperationStatus
from src.models.moodle_execution import ExecutionStatus
from src.models.workflow import WorkflowStatus
from src.models.workflow_event import EventType
from src.services.auth import hash_password
from src.services.course_plan.domain import CoursePlanDraft, CoursePlanWeekRecord
from src.services.course_plan.repository import CoursePlanRepository
from src.services.execution.errors import (
    EXECUTION_IN_PROGRESS,
    MOODLE_TARGET_NOT_SET,
    MOODLE_UNAVAILABLE,
    PLAN_NOT_APPROVED,
    ExecutionPreconditionError,
)
from src.services.execution.repository import ExecutionRepository
from src.services.execution.service import ExecutionService
from src.services.moodle_exceptions import MoodleAPIError
from src.services.moodle_integration_service import (
    MoodleCourseContents,
    MoodleSection,
    SectionWriteResult,
)
from src.services.rps.converter import DocumentConversion, DocumentConverter
from src.services.rps.service import RPSService
from src.services.rps.storage import LocalDocumentStorage
from src.services.user import UserRole, UserService
from src.services.workflow.broker import WorkflowEventBroker
from src.services.workflow.orchestrator import run_execution_workflow
from src.services.workflow.service import WorkflowService

PASSWORD = "SecretPassword123"
PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
MOODLE_COURSE_ID = 42


class UnusedConverter(DocumentConverter):
    """Upload tidak mengonversi dokumen; test eksekusi tidak butuh konversi."""

    name = "unused"

    @property
    def version(self) -> str:
        return "unused-1"

    async def convert(self, *, content: bytes, file_name: str) -> DocumentConversion:
        raise AssertionError("test eksekusi tidak boleh mengonversi dokumen")


class FakeMoodle:
    """Moodle palsu: menyimpan section per nomor dan dapat gagal per minggu."""

    def __init__(self, *, connected: bool = True) -> None:
        self.connected = connected
        self.fail_weeks: set[int] = set()
        self.sections: dict[int, str] = {}
        self.summaries: dict[int, str] = {}
        self.saved: list[tuple[int, bool]] = []

    async def get_status(self):
        return _FakeStatus(connected=self.connected)

    async def save_section(
        self,
        moodle_course_id: int,
        name: str,
        section_number: int | None = None,
        *,
        summary: str | None = None,
        section_id: int | None = None,
    ) -> SectionWriteResult:
        number = section_number or 0
        if number in self.fail_weeks:
            raise MoodleAPIError(
                "Moodle menolak rename section",
                code="invalidparameter",
                wsfunction="core_update_inplace_editable",
            )
        created = number not in self.sections
        self.sections[number] = name
        self.summaries[number] = summary or ""
        self.saved.append((number, created))
        return SectionWriteResult(
            section=MoodleSection(
                moodle_section_id=200 + number,
                section_number=number,
                name=name,
                summary="",
                visible=True,
            ),
            created=created,
        )

    async def get_course_contents(self, moodle_course_id: int) -> MoodleCourseContents:
        sections = [
            MoodleSection(
                moodle_section_id=100,
                section_number=0,
                name="General",
                summary="",
                visible=True,
            )
        ]
        sections += [
            MoodleSection(
                moodle_section_id=200 + number,
                section_number=number,
                name=name,
                summary="",
                visible=True,
            )
            for number, name in sorted(self.sections.items())
        ]
        return MoodleCourseContents(
            moodle_course_id=moodle_course_id, sections=sections
        )


@dataclass(frozen=True)
class _FakeStatus:
    connected: bool


class _SessionScope:
    def __init__(self, session) -> None:
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc_info) -> bool:
        return False


class FixedSessionFactory:
    """Session factory yang memakai session test (tidak membuka session baru)."""

    def __init__(self, session) -> None:
        self._session = session

    def __call__(self) -> _SessionScope:
        return _SessionScope(self._session)


@pytest.fixture
def storage(tmp_path) -> LocalDocumentStorage:
    return LocalDocumentStorage(tmp_path)


@pytest.fixture
def runner_env(monkeypatch, db_session):
    import src.services.workflow.orchestrator as orchestrator_module

    monkeypatch.setattr(
        orchestrator_module,
        "get_session_factory",
        lambda: FixedSessionFactory(db_session),
    )


@pytest_asyncio.fixture
async def owner_id(db_session, storage) -> str:
    suffix = shortuuid.uuid()[:10].lower()
    user = await UserService.from_session(db_session).create_user(
        username=f"instr{suffix}",
        firstname="Pengguna",
        lastname="Uji",
        email=f"instr-{suffix}@itk.ac.id",
        role=UserRole.INSTRUCTOR,
        password=hash_password(PASSWORD),
    )
    return user.id or ""


async def _prepare_workflow(
    session,
    owner_id: str,
    storage: LocalDocumentStorage,
    *,
    weeks: int = 2,
    approved: bool = True,
    moodle_course_id: int | None = MOODLE_COURSE_ID,
):
    """Workflow menunggu review + course plan (default APPROVED) siap dieksekusi."""
    rps_service = RPSService.from_session(
        session, storage=storage, converter=UnusedConverter()
    )
    uploaded = await rps_service.upload_rps(
        owner_id=owner_id, file_name="rps.pdf", content=PDF_BYTES
    )
    rps_id = uploaded.document.id or ""

    workflows = WorkflowService.from_session(session, broker=WorkflowEventBroker())
    workflow = await workflows.create_for_rps(
        owner_id=owner_id, rps_id=rps_id, total=1
    )
    await rps_service.attach_workflow(
        rps_id=rps_id, owner_id=owner_id, workflow_id=workflow.id or ""
    )
    started = await workflows.begin_run(workflow, total=1)
    waiting = await workflows.wait_for_review(started)
    if moodle_course_id is not None:
        waiting = await workflows.set_moodle_course_id(
            workflow_id=workflow.id or "",
            owner_id=owner_id,
            moodle_course_id=moodle_course_id,
        )

    plans = CoursePlanRepository(session)
    plan = await plans.create(
        CoursePlanDraft(
            workflow_id=workflow.id or "",
            rps_id=rps_id,
            course={"name": "Basis Data", "code": "IF123"},
            weeks=tuple(
                CoursePlanWeekRecord(
                    week_number=number, title=f"Materi minggu {number}"
                )
                for number in range(1, weeks + 1)
            ),
            plan_data={"weeks": weeks},
        )
    )
    if approved:
        plan = await plans.set_status(
            plan.id,
            CoursePlanStatus.APPROVED,
            approved_at=datetime.now(timezone.utc),
        )
    return waiting, plan


async def _start(session, moodle: FakeMoodle, workflow_id: str, owner_id: str):
    service = ExecutionService.from_session(session, moodle=moodle)
    return await service.start_structure(workflow_id=workflow_id, owner_id=owner_id)


async def _load(session, execution_id: str):
    return await ExecutionRepository(session).get(execution_id)


async def _load_workflow(session, workflow_id: str, owner_id: str):
    return await WorkflowService.from_session(session).get_workflow(
        workflow_id=workflow_id, owner_id=owner_id
    )


# --- Prasyarat ---------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "setup",
    ["plan_not_approved", "target_not_set", "moodle_unavailable", "in_progress"],
)
async def test_each_unmet_prerequisite_rejects_with_its_reason_code(
    db_session, owner_id, storage, setup
):
    moodle = FakeMoodle()
    if setup == "plan_not_approved":
        workflow, _ = await _prepare_workflow(
            db_session, owner_id, storage, approved=False
        )
    elif setup == "target_not_set":
        workflow, _ = await _prepare_workflow(
            db_session, owner_id, storage, moodle_course_id=None
        )
    elif setup == "moodle_unavailable":
        workflow, _ = await _prepare_workflow(db_session, owner_id, storage)
        moodle.connected = False
    else:
        workflow, _ = await _prepare_workflow(db_session, owner_id, storage)
        await WorkflowService.from_session(db_session).claim_execution(
            workflow_id=workflow.id or "", owner_id=owner_id
        )

    with pytest.raises(ExecutionPreconditionError) as raised:
        await _start(db_session, moodle, workflow.id or "", owner_id)

    expected = {
        "plan_not_approved": PLAN_NOT_APPROVED,
        "target_not_set": MOODLE_TARGET_NOT_SET,
        "moodle_unavailable": MOODLE_UNAVAILABLE,
        "in_progress": EXECUTION_IN_PROGRESS,
    }[setup]
    assert raised.value.reason == expected
    assert raised.value.details == [{"field": "reason", "message": expected}]
    assert raised.value.error_code == "INVALID_REQUEST"


# --- Eksekusi sukses ---------------------------------------------------------


@pytest.mark.asyncio
async def test_execution_applies_every_week_and_waits_for_review(
    db_session, owner_id, storage, runner_env
):
    workflow, plan = await _prepare_workflow(db_session, owner_id, storage, weeks=2)
    moodle = FakeMoodle()

    execution = await _start(db_session, moodle, workflow.id or "", owner_id)
    assert execution.status is ExecutionStatus.PENDING
    assert [operation.week_number for operation in execution.operations] == [1, 2]

    await run_execution_workflow(
        workflow_id=workflow.id or "",
        owner_id=owner_id,
        execution_id=execution.id or "",
        moodle=moodle,
    )

    stored = await _load(db_session, execution.id or "")
    assert stored is not None
    assert stored.status is ExecutionStatus.SUCCESS
    assert stored.course_plan_id == plan.id
    assert stored.moodle_course_id == MOODLE_COURSE_ID
    assert stored.summary.success == 2 and stored.summary.failed == 0
    assert stored.readback is not None and stored.readback["matches"] is True
    assert {operation.moodle_object_id for operation in stored.operations} == {
        "201",
        "202",
    }

    loaded = await _load_workflow(db_session, workflow.id or "", owner_id)
    assert loaded.status is WorkflowStatus.WAITING_FOR_REVIEW

    events = await WorkflowService.from_session(db_session).list_events(
        workflow_id=workflow.id or "", owner_id=owner_id
    )
    operation_events = [
        event for event in events if event.event == "WORKFLOW_MOODLE_OPERATION"
    ]
    assert len(operation_events) == 2
    assert all(
        event.event_type is EventType.OPERASI_MOODLE
        and event.stage == "moodle_execution"
        for event in operation_events
    )
    stages = {event.stage for event in events if event.stage}
    assert "moodle_execution" in stages


@pytest.mark.asyncio
async def test_second_execution_updates_sections_instead_of_adding(
    db_session, owner_id, storage, runner_env
):
    workflow, _ = await _prepare_workflow(db_session, owner_id, storage, weeks=2)
    moodle = FakeMoodle()

    first = await _start(db_session, moodle, workflow.id or "", owner_id)
    await run_execution_workflow(
        workflow_id=workflow.id or "",
        owner_id=owner_id,
        execution_id=first.id or "",
        moodle=moodle,
    )
    # Section minggu 1 dan 2 sudah dibuat oleh eksekusi pertama.
    assert [created for _, created in moodle.saved] == [True, True]

    second = await _start(db_session, moodle, workflow.id or "", owner_id)
    await run_execution_workflow(
        workflow_id=workflow.id or "",
        owner_id=owner_id,
        execution_id=second.id or "",
        moodle=moodle,
    )

    assert len(moodle.sections) == 2
    assert [created for _, created in moodle.saved[2:]] == [False, False]
    stored = await _load(db_session, second.id or "")
    assert stored is not None and stored.status is ExecutionStatus.SUCCESS


# --- Kegagalan dan retry -----------------------------------------------------


@pytest.mark.asyncio
async def test_failed_operation_marks_workflow_failed_and_retry_only_reruns_it(
    db_session, owner_id, storage, runner_env
):
    workflow, _ = await _prepare_workflow(db_session, owner_id, storage, weeks=2)
    moodle = FakeMoodle()
    moodle.fail_weeks = {2}

    execution = await _start(db_session, moodle, workflow.id or "", owner_id)
    await run_execution_workflow(
        workflow_id=workflow.id or "",
        owner_id=owner_id,
        execution_id=execution.id or "",
        moodle=moodle,
    )

    stored = await _load(db_session, execution.id or "")
    assert stored is not None
    assert stored.status is ExecutionStatus.FAILED
    assert stored.summary.success == 1 and stored.summary.failed == 1
    assert stored.error_message and "1 operasi gagal" in stored.error_message
    week_two = next(
        operation for operation in stored.operations if operation.week_number == 2
    )
    assert week_two.status is OperationStatus.FAILED
    assert week_two.error_message
    loaded = await _load_workflow(db_session, workflow.id or "", owner_id)
    assert loaded.status is WorkflowStatus.FAILED

    # Operasi yang berhasil tidak diulang; hanya minggu 2 yang dipanggil lagi.
    calls_before_retry = len(moodle.saved)
    moodle.fail_weeks.clear()
    service = ExecutionService.from_session(db_session, moodle=moodle)
    await service.retry_failed(
        workflow_id=workflow.id or "",
        owner_id=owner_id,
        execution_id=execution.id or "",
    )
    await run_execution_workflow(
        workflow_id=workflow.id or "",
        owner_id=owner_id,
        execution_id=execution.id or "",
        moodle=moodle,
    )

    retried = await _load(db_session, execution.id or "")
    assert retried is not None
    assert retried.status is ExecutionStatus.SUCCESS
    assert retried.summary.success == 2 and retried.summary.failed == 0
    week_two = next(
        operation for operation in retried.operations if operation.week_number == 2
    )
    assert week_two.status is OperationStatus.SUCCESS
    assert week_two.retry_count == 1
    assert len(moodle.saved) == calls_before_retry + 1
    assert moodle.saved[-1][0] == 2
    loaded = await _load_workflow(db_session, workflow.id or "", owner_id)
    assert loaded.status is WorkflowStatus.WAITING_FOR_REVIEW


@pytest.mark.asyncio
async def test_retry_is_rejected_for_a_successful_execution(
    db_session, owner_id, storage, runner_env
):
    workflow, _ = await _prepare_workflow(db_session, owner_id, storage, weeks=1)
    moodle = FakeMoodle()

    execution = await _start(db_session, moodle, workflow.id or "", owner_id)
    await run_execution_workflow(
        workflow_id=workflow.id or "",
        owner_id=owner_id,
        execution_id=execution.id or "",
        moodle=moodle,
    )

    service = ExecutionService.from_session(db_session, moodle=moodle)
    with pytest.raises(Exception) as raised:
        await service.retry_failed(
            workflow_id=workflow.id or "",
            owner_id=owner_id,
            execution_id=execution.id or "",
        )

    assert getattr(raised.value, "error_code", "") == "INVALID_REQUEST"
