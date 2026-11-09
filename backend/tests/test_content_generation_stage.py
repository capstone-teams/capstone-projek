"""Test integrasi tahap content generation pada orkestrator (BE-19.3).

Membuktikan acceptance criteria BE-19.3 tanpa memanggil LLM:

- generate seluruh minggu menyimpan konten dan berakhir ``WAITING_FOR_REVIEW``;
- event AKTIVITAS_AGENT tercatat per minggu dan per konten;
- regenerasi scope MINGGU/ITEM hanya membuat versi baru pada target scope;
- jenis konten mengikuti snapshot Activity Configuration;
- kegagalan satu konten tidak menghentikan konten minggu lain;
- generation ganda ditolak selama tahap masih berjalan.

Content Generation Service diganti stub; session database memakai pola
``FixedSessionFactory`` yang sama dengan test orkestrator lain.
"""

from __future__ import annotations

import hashlib

import pytest
import pytest_asyncio
import shortuuid

from src.models.course_plan import CoursePlan, CoursePlanStatus
from src.models.course_plan_week import CoursePlanWeek
from src.models.rps import RPS, RPSStatus
from src.models.validation_result import ValidationStatus
from src.schemas.content import (
    AssignmentOutput,
    LearningMaterialOutput,
    MaterialSection,
    QuizOutput,
    QuizConfig,
    QuizQuestion,
    QuizOption,
    RubricCriterion,
    WeekContext,
)
from src.services.auth import hash_password
from src.services.content import ContentKind, ContentReviewService
from src.services.content.generate_service import (
    ContentGenerationError,
    WeekResult,
    list_weeks,
)
from src.services.content.errors import ContentStateError
from src.services.content.generation import (
    ContentGenerationService,
    ContentJob,
    RegenerationScope,
)
from src.services.user import UserRole, UserService
from src.services.workflow.broker import WorkflowEventBroker
from src.services.workflow.domain import WorkflowRecord
from src.services.workflow.orchestrator import run_content_generation_workflow
from src.services.workflow.repository import WorkflowRepository
from src.services.workflow.service import WorkflowService

PASSWORD = "SecretPassword123"


class _SessionScope:
    def __init__(self, session) -> None:
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc_info) -> bool:
        return False


class FixedSessionFactory:
    def __init__(self, session) -> None:
        self._session = session

    def __call__(self):
        return _SessionScope(self._session)


def _material(week: int) -> LearningMaterialOutput:
    return LearningMaterialOutput(
        title=f"Materi minggu {week}",
        sub_cpmk_codes=["SUB-1"],
        learning_objectives=["Mahasiswa memahami topik"],
        sections=[MaterialSection(heading="Pendahuluan", body_markdown="Isi.")],
        references=[],
    )


def _assignment(week: int) -> AssignmentOutput:
    return AssignmentOutput(
        title=f"Tugas minggu {week}",
        sub_cpmk_codes=["SUB-1"],
        instructions_markdown="Kerjakan tugas.",
        expected_outputs=["Dokumen"],
        rubric=[
            RubricCriterion(
                criterion="Ketepatan",
                description="Jawaban tepat",
                weight_percent=100,
            )
        ],
    )


def _quiz(week: int) -> QuizOutput:
    return QuizOutput(
        title=f"Kuis minggu {week}",
        sub_cpmk_codes=["SUB-1"],
        description="Kuis singkat.",
        config=QuizConfig(
            time_limit_minutes=10,
            max_attempts=2,
            shuffle_questions=True,
            passing_score_percent=70,
        ),
        questions=[
            QuizQuestion(
                question_text="Pilih A?",
                options=[
                    QuizOption(key="A", text="Benar"),
                    QuizOption(key="B", text="Salah"),
                ],
                correct_option_key="A",
                explanation="A benar.",
            )
        ],
    )


_OUTPUTS = {
    "LEARNING_MATERIAL": _material,
    "ASSIGNMENT": _assignment,
    "QUIZ": _quiz,
}


class StubGenerator:
    """Stub ``generate_contents``: mencatat panggilan dan minggu yang gagal."""

    def __init__(self, contexts: list[WeekContext], *, fail_weeks=()) -> None:
        self.contexts = {ctx.week_number: ctx for ctx in contexts}
        self.fail_weeks = set(fail_weeks)
        self.calls: list[dict] = []

    async def __call__(
        self,
        db,
        course_plan_id,
        *,
        week_numbers=None,
        content_types=None,
        **kwargs,
    ):
        week = week_numbers[0]
        kind = content_types[0]
        self.calls.append(
            {
                "week": week,
                "kind": kind,
                "previous_version": kwargs.get("previous_version"),
                "revision_notes": kwargs.get("revision_notes"),
            }
        )
        ctx = self.contexts[week]
        if week in self.fail_weeks:
            return [
                WeekResult(
                    ctx=ctx,
                    error=ContentGenerationError(
                        "provider gagal", reason_code="PROVIDER_ERROR"
                    ),
                    content_type=kind,
                )
            ]
        return [
            WeekResult(
                ctx=ctx,
                material=_OUTPUTS[kind](week),
                content_type=kind,
            )
        ]


@pytest_asyncio.fixture
async def owner_id(db_session) -> str:
    suffix = shortuuid.uuid()[:10].lower()
    user = await UserService.from_session(db_session).create_user(
        username=f"content{suffix}",
        firstname="Dosen",
        lastname="Uji",
        email=f"content-{suffix}@itk.ac.id",
        role=UserRole.INSTRUCTOR,
        password=hash_password(PASSWORD),
    )
    return user.id or ""


@pytest_asyncio.fixture
async def workspace(db_session, owner_id):
    suffix = shortuuid.uuid()[:10].lower()
    rps = RPS(
        owner_id=owner_id,
        file_name="rps.pdf",
        file_type="pdf",
        file_path="rps/rps.pdf",
        file_hash=hashlib.sha256(f"be-19-3-{suffix}".encode()).hexdigest(),
        status=RPSStatus.ANALYZED,
    )
    db_session.add(rps)
    await db_session.flush()

    workflow = await WorkflowRepository(db_session).create(
        WorkflowRecord.create(owner_id=owner_id, rps_id=rps.id, progress_total=2)
    )
    plan = CoursePlan(
        workflow_id=workflow.id,
        rps_id=rps.id,
        version=1,
        weeks_count=2,
        status=CoursePlanStatus.APPROVED,
        plan_data={"course": {"title": "Basis Data", "code": "IF2230"}},
        activity_configuration={
            "learning_material": True,
            "learning_resource": False,
            "assignment": False,
            "quiz": False,
        },
        validation_result={"passed": True, "issues": []},
    )
    db_session.add(plan)
    await db_session.flush()

    weeks = [
        CoursePlanWeek(
            course_plan_id=plan.id,
            week_number=number,
            title=f"Topik minggu {number}",
            week_type="regular",
            learning_outcomes=["SUB-1"],
            topics=[f"Topik {number}"],
            methods=["Ceramah"],
        )
        for number in (1, 2)
    ]
    db_session.add_all(weeks)
    await db_session.flush()

    service = WorkflowService.from_session(
        db_session, broker=WorkflowEventBroker()
    )
    workflow = await service.wait_for_review(workflow)
    return workflow, plan, weeks


@pytest_asyncio.fixture
async def generator(db_session, workspace):
    _workflow, plan, _weeks = workspace
    contexts = await list_weeks(db_session, plan.id)
    return StubGenerator(contexts)


@pytest.fixture
def runner_env(monkeypatch, db_session, generator):
    import src.services.content.generation as generation_module
    import src.services.workflow.orchestrator as orchestrator_module

    monkeypatch.setattr(
        orchestrator_module,
        "get_session_factory",
        lambda: FixedSessionFactory(db_session),
    )
    monkeypatch.setattr(
        generation_module, "generate_contents", generator
    )
    return generator


async def _events(db_session, workflow):
    return await WorkflowService.from_session(
        db_session, broker=WorkflowEventBroker()
    ).list_events(workflow_id=workflow.id or "", owner_id=workflow.owner_id)


async def _stored(db_session, workflow):
    records = await ContentReviewService.from_session(db_session).list_contents(
        workflow_id=workflow.id or "", owner_id=workflow.owner_id
    )
    return records, None


def _job(workflow, *, scope=None, weeks=None, content_id=None, notes=None):
    return ContentJob(
        week_numbers=weeks,
        content_id=content_id,
        scope=scope,
        notes=notes,
    )


@pytest.mark.asyncio
async def test_generate_all_weeks_stores_content_and_waits_for_review(
    db_session, workspace, runner_env
):
    workflow, _plan, _weeks = workspace
    service = ContentGenerationService.from_session(db_session)
    await service.start(
        workflow_id=workflow.id or "",
        owner_id=workflow.owner_id,
        job=_job(workflow),
    )

    await run_content_generation_workflow(
        workflow_id=workflow.id or "", owner_id=workflow.owner_id
    )

    loaded = await WorkflowService.from_session(
        db_session, broker=WorkflowEventBroker()
    ).get_workflow(workflow_id=workflow.id or "", owner_id=workflow.owner_id)
    assert loaded.status.value == "WAITING_FOR_REVIEW"
    assert (loaded.progress_completed, loaded.progress_total) == (2, 2)

    records, _ = await _stored(db_session, workflow)
    assert len(records) == 2
    assert {record.week_number for record in records} == {1, 2}
    assert all(record.status.value == "DRAFT" for record in records)
    assert all(
        record.validation is not None
        and record.validation.status is ValidationStatus.PASSED
        for record in records
    )

    events = await _events(db_session, workflow)
    names = [event.event for event in events]
    assert names.count("WORKFLOW_STAGE_STARTED") == 2
    assert names.count("WORKFLOW_STAGE_COMPLETED") == 2
    assert names.count("WORKFLOW_CONTENT_VALIDATED") == 2
    assert names.count("WORKFLOW_WEEK_COMPLETED") == 2
    assert names[-1] == "WORKFLOW_WAITING_FOR_REVIEW"

    stages = {
        event.stage for event in events if event.event == "WORKFLOW_STAGE_STARTED"
    }
    assert stages == {"content_generation", "validation"}


@pytest.mark.asyncio
async def test_regeneration_minggu_only_versions_that_week(
    db_session, workspace, runner_env
):
    workflow, _plan, weeks = workspace
    service = ContentGenerationService.from_session(db_session)
    await service.start(
        workflow_id=workflow.id or "",
        owner_id=workflow.owner_id,
        job=_job(workflow),
    )
    await run_content_generation_workflow(
        workflow_id=workflow.id or "", owner_id=workflow.owner_id
    )
    before, _ = await _stored(db_session, workflow)
    week_two = next(record for record in before if record.week_number == 2)

    runner_env.calls.clear()
    await service.start(
        workflow_id=workflow.id or "",
        owner_id=workflow.owner_id,
        job=_job(
            workflow,
            scope=RegenerationScope.MINGGU,
            weeks=(2,),
            notes="Perjelas contoh minggu 2.",
        ),
    )
    await run_content_generation_workflow(
        workflow_id=workflow.id or "",
        owner_id=workflow.owner_id,
        week_numbers=(2,),
        scope="MINGGU",
        notes="Perjelas contoh minggu 2.",
    )

    after, _ = await _stored(db_session, workflow)
    by_week = {record.week_number: record for record in after}
    assert len(after) == 2
    assert by_week[1].version == 1
    assert by_week[2].version == 2
    assert by_week[2].content_key == week_two.content_key
    assert runner_env.calls[0]["previous_version"]
    assert runner_env.calls[0]["revision_notes"] == "Perjelas contoh minggu 2."


@pytest.mark.asyncio
async def test_regeneration_item_only_versions_that_content(
    db_session, workspace, runner_env
):
    workflow, _plan, _weeks = workspace
    service = ContentGenerationService.from_session(db_session)
    await service.start(
        workflow_id=workflow.id or "",
        owner_id=workflow.owner_id,
        job=_job(workflow),
    )
    await run_content_generation_workflow(
        workflow_id=workflow.id or "", owner_id=workflow.owner_id
    )
    before, _ = await _stored(db_session, workflow)
    target = next(record for record in before if record.week_number == 1)

    await service.start(
        workflow_id=workflow.id or "",
        owner_id=workflow.owner_id,
        job=_job(
            workflow,
            scope=RegenerationScope.ITEM,
            content_id=target.id,
            notes="Ubah gaya penyampaian.",
        ),
    )
    await run_content_generation_workflow(
        workflow_id=workflow.id or "",
        owner_id=workflow.owner_id,
        content_id=target.id,
        scope="ITEM",
        notes="Ubah gaya penyampaian.",
    )

    after, _ = await _stored(db_session, workflow)
    by_week = {record.week_number: record for record in after}
    assert by_week[1].version == 2
    assert by_week[2].version == 1
    assert len(after) == 2


@pytest.mark.asyncio
async def test_activity_configuration_snapshot_limits_generated_kinds(
    db_session, workspace, runner_env
):
    workflow, plan, _weeks = workspace
    plan.activity_configuration = {
        "learning_material": False,
        "learning_resource": False,
        "assignment": True,
        "quiz": False,
    }
    await db_session.flush()

    service = ContentGenerationService.from_session(db_session)
    await service.start(
        workflow_id=workflow.id or "",
        owner_id=workflow.owner_id,
        job=_job(workflow),
    )
    await run_content_generation_workflow(
        workflow_id=workflow.id or "", owner_id=workflow.owner_id
    )

    assert [call["kind"] for call in runner_env.calls] == [
        "ASSIGNMENT",
        "ASSIGNMENT",
    ]
    records, _ = await _stored(db_session, workflow)
    assert {record.kind for record in records} == {ContentKind.ASSIGNMENT}


@pytest.mark.asyncio
async def test_partial_failure_does_not_stop_other_weeks(
    db_session, workspace, runner_env
):
    workflow, _plan, _weeks = workspace
    runner_env.fail_weeks = {1}
    service = ContentGenerationService.from_session(db_session)
    await service.start(
        workflow_id=workflow.id or "",
        owner_id=workflow.owner_id,
        job=_job(workflow),
    )
    await run_content_generation_workflow(
        workflow_id=workflow.id or "", owner_id=workflow.owner_id
    )

    loaded = await WorkflowService.from_session(
        db_session, broker=WorkflowEventBroker()
    ).get_workflow(workflow_id=workflow.id or "", owner_id=workflow.owner_id)
    assert loaded.status.value == "WAITING_FOR_REVIEW"

    records, _ = await _stored(db_session, workflow)
    failed = next(record for record in records if record.week_number == 1)
    succeeded = next(record for record in records if record.week_number == 2)
    assert failed.validation.status is ValidationStatus.FAILED
    assert succeeded.validation.status is ValidationStatus.PASSED

    names = [event.event for event in await _events(db_session, workflow)]
    assert "WORKFLOW_CONTENT_FAILED" in names
    assert names[-1] == "WORKFLOW_WAITING_FOR_REVIEW"


@pytest.mark.asyncio
async def test_generation_cannot_start_twice(
    db_session, workspace, runner_env
):
    workflow, _plan, _weeks = workspace
    service = ContentGenerationService.from_session(db_session)
    await service.start(
        workflow_id=workflow.id or "",
        owner_id=workflow.owner_id,
        job=_job(workflow),
    )

    with pytest.raises(ContentStateError):
        await service.start(
            workflow_id=workflow.id or "",
            owner_id=workflow.owner_id,
            job=_job(workflow),
        )
