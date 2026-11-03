"""Test model, repository, dan service course plan (BE-14.1).

Membuktikan acceptance criteria BE-14.1:

- course plan 16 minggu dapat disimpan dan dibaca kembali dengan urutan minggu
  yang benar;
- menyimpan versi kedua tidak mengubah versi pertama;
- hanya satu versi ``APPROVED`` per workflow (dijaga database).

Database memakai PostgreSQL pada fixture :func:`conftest.db_session` supaya
JSONB dan partial unique index benar-benar terpakai.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
import pytest_asyncio
import shortuuid
from sqlalchemy.exc import IntegrityError

from src.models.course_plan import CoursePlanStatus
from src.models.rps import RPS, RPSStatus
from src.schemas.course_plan import (
    CoursePlanActivityType,
    CoursePlanCourse,
    CoursePlanOutput,
    CoursePlanWeek,
)
from src.services.auth import hash_password
from src.services.course_plan import CoursePlanService
from src.services.course_plan.domain import CoursePlanRecord
from src.services.course_plan.errors import CoursePlanStateError
from src.services.course_plan.repository import CoursePlanRepository
from src.services.user import UserRole, UserService
from src.services.workflow.domain import WorkflowRecord
from src.services.workflow.errors import WorkflowNotFoundError
from src.services.workflow.repository import WorkflowRepository

PASSWORD = "SecretPassword123"

RPS_WEEKS = {
    week: {"week": week, "week_type": "uts" if week == 8 else "regular"}
    for week in range(1, 17)
}


async def _create_instructor(session, label: str) -> str:
    suffix = shortuuid.uuid()[:10].lower()
    user = await UserService.from_session(session).create_user(
        username=f"{label}{suffix}",
        firstname="Dosen",
        lastname="Uji",
        email=f"{label}-{suffix}@itk.ac.id",
        role=UserRole.INSTRUCTOR,
        password=hash_password(PASSWORD),
    )
    return user.id or ""


@pytest_asyncio.fixture
async def owner_id(db_session) -> str:
    return await _create_instructor(db_session, "plan")


@pytest_asyncio.fixture
async def workflow(db_session, owner_id) -> WorkflowRecord:
    rps = RPS(
        owner_id=owner_id,
        file_name="rps.pdf",
        file_type="pdf",
        file_path="rps/rps.pdf",
        file_hash=shortuuid.uuid(),
        status=RPSStatus.ANALYZED,
    )
    db_session.add(rps)
    await db_session.flush()

    return await WorkflowRepository(db_session).create(
        WorkflowRecord.create(owner_id=owner_id, rps_id=rps.id, progress_total=2)
    )


def _plan_output(*, weeks: int = 16, title_suffix: str = "") -> CoursePlanOutput:
    return CoursePlanOutput(
        course=CoursePlanCourse(title="Basis Data", code="IF2230"),
        weeks=[
            CoursePlanWeek(
                week_number=number,
                title=f"Materi minggu {number}{title_suffix}",
                learning_outcomes=[f"SUB-{number}"],
                objectives=[f"Mahasiswa memahami materi minggu {number}"],
                topics=[f"Topik {number}"],
                teaching_methods=["Ceramah", "Praktikum"],
                planned_activities=[CoursePlanActivityType.LEARNING_MATERIAL],
            )
            for number in range(1, weeks + 1)
        ],
    )


async def _create_version(
    service: CoursePlanService,
    workflow: WorkflowRecord,
    *,
    weeks: int = 16,
    title_suffix: str = "",
) -> CoursePlanRecord:
    return await service.create_version(
        workflow=workflow,
        output=_plan_output(weeks=weeks, title_suffix=title_suffix),
        rps_weeks=RPS_WEEKS if weeks == 16 else None,
        validation_result={"passed": True, "issues": []},
        activity_configuration={"learning_material": True, "assignment": False},
        prompt_version="course_planning/v1",
        model_name="model-uji",
    )


def _workflow_args(workflow: WorkflowRecord) -> dict:
    return {"workflow_id": workflow.id or "", "owner_id": workflow.owner_id}


@pytest.mark.asyncio
async def test_plan_with_16_weeks_is_stored_and_read_in_week_order(
    db_session, workflow
):
    service = CoursePlanService.from_session(db_session)

    stored = await _create_version(service, workflow)

    assert stored.version == 1
    assert stored.status is CoursePlanStatus.DRAFT
    assert stored.weeks_count == 16
    assert [week.week_number for week in stored.weeks] == list(range(1, 17))
    assert stored.course["title"] == "Basis Data"
    assert stored.prompt_version == "course_planning/v1"
    assert stored.model_name == "model-uji"
    assert stored.validation_passed is True

    # Penanda UTS dan referensi baris RPS disalin dari RPS Analysis.
    assert stored.weeks[7].week_type == "uts"
    assert stored.weeks[7].rps_week == 8
    assert stored.weeks[0].week_type == "regular"
    assert stored.weeks[0].rps_week == 1

    loaded = await service.get_version(**_workflow_args(workflow), version=1)
    assert loaded.id == stored.id
    assert loaded.weeks[0].title == "Materi minggu 1"


@pytest.mark.asyncio
async def test_second_version_does_not_change_the_first(db_session, workflow):
    service = CoursePlanService.from_session(db_session)

    first = await _create_version(service, workflow)
    second = await _create_version(service, workflow, title_suffix=" (revisi)")

    assert second.version == first.version + 1
    assert second.id != first.id
    assert second.weeks[0].title == "Materi minggu 1 (revisi)"

    loaded_first = await service.get_version(**_workflow_args(workflow), version=1)
    assert loaded_first.weeks[0].title == "Materi minggu 1"
    assert loaded_first.status is CoursePlanStatus.DRAFT

    latest = await service.get_latest(**_workflow_args(workflow))
    assert latest.version == 2

    versions = await service.list_versions(**_workflow_args(workflow))
    assert [record.version for record in versions] == [2, 1]


@pytest.mark.asyncio
async def test_database_allows_only_one_approved_version_per_workflow(
    db_session, workflow
):
    service = CoursePlanService.from_session(db_session)
    repository = CoursePlanRepository(db_session)

    first = await _create_version(service, workflow)
    second = await _create_version(service, workflow)

    approved_at = datetime.now(timezone.utc)
    approved = await repository.set_status(
        first.id, CoursePlanStatus.APPROVED, approved_at=approved_at
    )
    assert approved is not None
    assert approved.status is CoursePlanStatus.APPROVED
    assert approved.approved_at is not None

    with pytest.raises(IntegrityError):
        await repository.set_status(
            second.id, CoursePlanStatus.APPROVED, approved_at=approved_at
        )
    await db_session.rollback()


@pytest.mark.asyncio
async def test_new_version_is_rejected_after_approval(db_session, workflow):
    service = CoursePlanService.from_session(db_session)
    repository = CoursePlanRepository(db_session)

    stored = await _create_version(service, workflow)
    await repository.set_status(
        stored.id,
        CoursePlanStatus.APPROVED,
        approved_at=datetime.now(timezone.utc),
    )

    with pytest.raises(CoursePlanStateError):
        await _create_version(service, workflow)


@pytest.mark.asyncio
async def test_plan_is_scoped_to_the_workflow_owner(db_session, workflow):
    other_owner = await _create_instructor(db_session, "other")
    service = CoursePlanService.from_session(db_session)
    await _create_version(service, workflow)

    with pytest.raises(WorkflowNotFoundError):
        await service.get_latest(
            workflow_id=workflow.id or "", owner_id=other_owner
        )


def test_duplicate_week_numbers_are_rejected():
    with pytest.raises(ValueError):
        CoursePlanOutput(
            course=CoursePlanCourse(title="Basis Data"),
            weeks=[
                CoursePlanWeek(week_number=1, title="Minggu 1"),
                CoursePlanWeek(week_number=1, title="Minggu 1 lagi"),
            ],
        )
