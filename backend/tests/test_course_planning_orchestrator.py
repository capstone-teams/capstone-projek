"""Test integrasi tahap course planning pada orkestrator (BE-14.3).

Membuktikan acceptance criteria BE-14.3 tanpa memanggil LLM:

- satu RPS contoh menghasilkan course plan versi 1 dan workflow berakhir
  ``WAITING_FOR_REVIEW``;
- regenerasi setelah reject memakai versi sebelumnya + catatan revisi dan
  menghasilkan versi 2 tanpa mengubah versi 1;
- kegagalan Course Planning Service menghasilkan status ``FAILED`` dan satu
  event ``ERROR_FAILURE``;
- setiap transisi tahap tercatat sebagai ``WorkflowEvent``.

Planner diganti stub yang dapat diamati; session database memakai pola
``FixedSessionFactory`` yang sama dengan test orkestrator BE-11.2.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pytest
import pytest_asyncio
import shortuuid

from src.models.course_plan import CoursePlanStatus
from src.models.rps import RPS, RPSStatus
from src.schemas.course_plan import (
    CoursePlanActivityType,
    CoursePlanCourse,
    CoursePlanOutput,
    CoursePlanWeek,
)
from src.schemas.rps_structured import RPSStructuredData
from src.services.auth import hash_password
from src.services.course_plan import CoursePlanService
from src.services.course_plan.errors import CoursePlanNotFoundError
from src.services.course_plan.planner import PlannedCoursePlan, PlanningRequest
from src.services.course_plan.repository import CoursePlanRepository
from src.services.user import UserRole, UserService
from src.services.workflow.broker import WorkflowEventBroker
from src.services.workflow.domain import WorkflowRecord
from src.services.workflow.orchestrator import run_course_planning_workflow
from src.services.workflow.repository import WorkflowRepository
from src.services.workflow.service import WorkflowService

PASSWORD = "SecretPassword123"

ANALYSIS: dict = {
    "course": {"name": "Basis Data", "code": "IF2230"},
    "sub_cpmk": [
        {"id": "SUB-1", "description": "Menjelaskan konsep basis data"},
        {"id": "SUB-2", "description": "Mengevaluasi pemahaman"},
    ],
    "weeks": [
        {"week": 1, "week_type": "regular", "topics": ["Pengenalan Basis Data"]},
        {"week": 2, "week_type": "uts", "topics": []},
    ],
}


class StubPlanner:
    """Planner palsu: mencatat request, dapat mengemit retry atau gagal."""

    def __init__(
        self,
        *,
        fail: bool = False,
        retry: bool = False,
        output: CoursePlanOutput | None = None,
    ) -> None:
        self.fail = fail
        self.retry = retry
        self.output = output or _output()
        self.requests: list[PlanningRequest] = []

    async def generate(self, request, *, emit_event=None):
        self.requests.append(request)

        if emit_event is not None:
            await emit_event(
                event="LLM_CALLING", message="Memanggil model.", attempt=1
            )
        if self.retry and emit_event is not None:
            await emit_event(
                event="RETRY_FIX",
                message="Memperbaiki output.",
                attempt=1,
                reason_code="SCHEMA_VALIDATION_FAILED",
            )
            await emit_event(
                event="LLM_CALLING", message="Memanggil model lagi.", attempt=2
            )
        if self.fail:
            if emit_event is not None:
                await emit_event(
                    event="PLANNING_FAILED",
                    message="Penyedia model gagal.",
                    attempt=2,
                    reason_code="LLM_PROVIDER_ERROR",
                )
            from src.services.course_plan.errors import CoursePlanGenerationError

            raise CoursePlanGenerationError("stub sengaja gagal")

        return PlannedCoursePlan(
            output=self.output,
            prompt_version="course_planning/v1",
            model_name="stub-model",
            attempts=2 if self.retry else 1,
        )


def _output(*, exam_topics: list[str] | None = None) -> CoursePlanOutput:
    return CoursePlanOutput(
        course=CoursePlanCourse(title="Basis Data", code="IF2230"),
        weeks=[
            CoursePlanWeek(
                week_number=1,
                title="Pengenalan Basis Data",
                learning_outcomes=["SUB-1"],
                objectives=["Mahasiswa memahami konsep basis data"],
                topics=["Pengenalan Basis Data"],
                teaching_methods=["Ceramah"],
                planned_activities=[CoursePlanActivityType.LEARNING_MATERIAL],
            ),
            CoursePlanWeek(
                week_number=2,
                title="Ujian Tengah Semester",
                learning_outcomes=["SUB-2"],
                objectives=["Mengevaluasi pemahaman"],
                topics=exam_topics or [],
                teaching_methods=[],
                planned_activities=[],
            ),
        ],
    )


class _SessionScope:
    def __init__(self, session) -> None:
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc_info) -> bool:
        return False


class FixedSessionFactory:
    """Session factory palsu yang selalu menyerahkan session milik test."""

    def __init__(self, session) -> None:
        self._session = session

    def __call__(self):
        return _SessionScope(self._session)


@pytest_asyncio.fixture
async def owner_id(db_session) -> str:
    suffix = shortuuid.uuid()[:10].lower()
    user = await UserService.from_session(db_session).create_user(
        username=f"planning{suffix}",
        firstname="Dosen",
        lastname="Uji",
        email=f"planning-{suffix}@itk.ac.id",
        role=UserRole.INSTRUCTOR,
        password=hash_password(PASSWORD),
    )
    return user.id or ""


@pytest_asyncio.fixture
async def workflow(db_session, owner_id) -> WorkflowRecord:
    """Workflow dengan RPS yang sudah dianalisis dan menunggu tindakan dosen."""
    rps = RPS(
        owner_id=owner_id,
        file_name="rps.pdf",
        file_type="pdf",
        file_path="rps/rps.pdf",
        file_hash=hashlib.sha256(b"be-14-rps").hexdigest(),
        schema_version="2.0",
        status=RPSStatus.ANALYZED,
        structured_data=RPSStructuredData.model_validate(ANALYSIS).model_dump(
            mode="json"
        ),
        analyzed_at=datetime.now(timezone.utc),
    )
    db_session.add(rps)
    await db_session.flush()

    created = await WorkflowRepository(db_session).create(
        WorkflowRecord.create(owner_id=owner_id, rps_id=rps.id, progress_total=2)
    )
    service = WorkflowService.from_session(
        db_session, broker=WorkflowEventBroker()
    )
    return await service.wait_for_review(created)


@pytest.fixture
def runner_env(monkeypatch, db_session):
    import src.services.workflow.orchestrator as orchestrator_module

    monkeypatch.setattr(
        orchestrator_module,
        "get_session_factory",
        lambda: FixedSessionFactory(db_session),
    )
    return db_session


async def _events(db_session, workflow):
    return await WorkflowService.from_session(
        db_session, broker=WorkflowEventBroker()
    ).list_events(workflow_id=workflow.id or "", owner_id=workflow.owner_id)


async def _claimed(db_session, workflow, *, regenerate=False, instruction=None):
    return await CoursePlanService.from_session(db_session).start_planning(
        workflow_id=workflow.id or "",
        owner_id=workflow.owner_id,
        regenerate=regenerate,
        instruction=instruction,
    )


@pytest.mark.asyncio
async def test_generation_stores_version_one_and_waits_for_review(
    db_session, workflow, runner_env
):
    planner = StubPlanner()
    await _claimed(db_session, workflow)

    await run_course_planning_workflow(
        workflow_id=workflow.id or "",
        owner_id=workflow.owner_id,
        planner=planner,
    )

    loaded = await WorkflowService.from_session(
        db_session, broker=WorkflowEventBroker()
    ).get_workflow(workflow_id=workflow.id or "", owner_id=workflow.owner_id)
    assert loaded.status.value == "WAITING_FOR_REVIEW"
    assert (loaded.progress_completed, loaded.progress_total) == (2, 2)

    record = await CoursePlanService.from_session(db_session).get_latest(
        workflow_id=workflow.id or "", owner_id=workflow.owner_id
    )
    assert record.version == 1
    assert record.status is CoursePlanStatus.DRAFT
    assert record.weeks_count == 2
    assert record.validation_passed is True
    assert record.prompt_version == "course_planning/v1"
    assert record.model_name == "stub-model"

    # Konteks yang dikirim ke planner berisi RPS, konteks dosen, dan activity
    # configuration (issue BE-14.3).
    request = planner.requests[0]
    assert request.rps_structured["course"]["name"] == "Basis Data"
    assert request.instructor_context["activity_configuration"]["learning_material"] is True
    assert request.previous_plan is None
    assert request.revision_notes is None

    events = await _events(db_session, workflow)
    names = [event.event for event in events]
    assert names.count("WORKFLOW_STAGE_STARTED") == 2
    assert names.count("WORKFLOW_STAGE_COMPLETED") == 2
    assert "WORKFLOW_PLAN_GENERATED" in names
    assert names[-1] == "WORKFLOW_WAITING_FOR_REVIEW"
    stages = [event.stage for event in events if event.event == "WORKFLOW_STAGE_STARTED"]
    assert stages == ["course_planning", "validation"]


@pytest.mark.asyncio
async def test_regeneration_uses_previous_plan_and_revision_notes(
    db_session, workflow, runner_env
):
    service = CoursePlanService.from_session(db_session)
    first = await service.create_version(
        workflow=workflow,
        output=_output(),
        validation_result={"passed": False, "issues": []},
    )
    await CoursePlanRepository(db_session).set_status(
        first.id,
        CoursePlanStatus.REJECTED,
        revision_notes="Minggu 2 jangan berisi materi.",
    )

    planner = StubPlanner()
    await _claimed(
        db_session, workflow, regenerate=True, instruction="Pindahkan topik ke minggu 3."
    )
    await run_course_planning_workflow(
        workflow_id=workflow.id or "",
        owner_id=workflow.owner_id,
        instruction="Pindahkan topik ke minggu 3.",
        planner=planner,
    )

    request = planner.requests[0]
    assert request.previous_plan is not None
    assert request.revision_notes == "Minggu 2 jangan berisi materi."
    assert request.instruction == "Pindahkan topik ke minggu 3."

    latest = await service.get_latest(
        workflow_id=workflow.id or "", owner_id=workflow.owner_id
    )
    assert latest.version == 2
    assert latest.regeneration_instruction == "Pindahkan topik ke minggu 3."

    original = await service.get_version(
        workflow_id=workflow.id or "", owner_id=workflow.owner_id, version=1
    )
    assert original.status is CoursePlanStatus.REJECTED
    assert original.revision_notes == "Minggu 2 jangan berisi materi."


@pytest.mark.asyncio
async def test_retry_moves_workflow_to_retrying_then_back(
    db_session, workflow, runner_env
):
    planner = StubPlanner(retry=True)
    await _claimed(db_session, workflow)

    await run_course_planning_workflow(
        workflow_id=workflow.id or "",
        owner_id=workflow.owner_id,
        planner=planner,
    )

    events = await _events(db_session, workflow)
    retries = [event for event in events if event.event == "WORKFLOW_RETRY"]
    assert len(retries) == 1
    assert retries[0].event_type.value == "RETRY_FIX"
    assert retries[0].metadata_["reason_code"] == "SCHEMA_VALIDATION_FAILED"

    loaded = await WorkflowService.from_session(
        db_session, broker=WorkflowEventBroker()
    ).get_workflow(workflow_id=workflow.id or "", owner_id=workflow.owner_id)
    assert loaded.status.value == "WAITING_FOR_REVIEW"


@pytest.mark.asyncio
async def test_service_failure_marks_workflow_failed_with_one_error_event(
    db_session, workflow, runner_env
):
    planner = StubPlanner(fail=True)
    await _claimed(db_session, workflow)

    await run_course_planning_workflow(
        workflow_id=workflow.id or "",
        owner_id=workflow.owner_id,
        planner=planner,
    )

    loaded = await WorkflowService.from_session(
        db_session, broker=WorkflowEventBroker()
    ).get_workflow(workflow_id=workflow.id or "", owner_id=workflow.owner_id)
    assert loaded.status.value == "FAILED"

    events = await _events(db_session, workflow)
    failures = [event for event in events if event.event == "WORKFLOW_FAILED"]
    assert len(failures) == 1
    assert failures[0].event_type.value == "ERROR_FAILURE"
    assert failures[0].stage == "course_planning"

    with pytest.raises(CoursePlanNotFoundError):
        await CoursePlanService.from_session(db_session).get_latest(
            workflow_id=workflow.id or "", owner_id=workflow.owner_id
        )


@pytest.mark.asyncio
async def test_academic_validation_findings_are_stored_with_the_version(
    db_session, workflow, runner_env
):
    planner = StubPlanner(output=_output(exam_topics=["Materi baru"]))
    await _claimed(db_session, workflow)

    await run_course_planning_workflow(
        workflow_id=workflow.id or "",
        owner_id=workflow.owner_id,
        planner=planner,
    )

    record = await CoursePlanService.from_session(db_session).get_latest(
        workflow_id=workflow.id or "", owner_id=workflow.owner_id
    )
    codes = [issue["code"] for issue in record.validation_result["issues"]]
    assert "EXAM_WEEK_HAS_MATERIAL" in codes
    assert record.validation_passed is False
