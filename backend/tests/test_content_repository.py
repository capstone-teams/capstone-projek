"""Test model dan repository konten hasil generation (BE-19.1).

Membuktikan acceptance criteria BE-19.1:

- empat jenis konten (learning material, resource, assignment, quiz) dapat
  disimpan dan dibaca kembali beserta hasil validasinya;
- penyimpanan versi kedua tidak mengubah versi pertama;
- ``content_key`` tetap sama antarversi, sedangkan nomor versi naik.

Database memakai PostgreSQL pada fixture :func:`conftest.db_session` supaya
JSONB, enum, dan unique constraint benar-benar terpakai.
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
from src.services.auth import hash_password
from src.services.content import (
    ApprovalStatus,
    ContentDraft,
    ContentKind,
    ContentRepository,
    content_key_for,
)
from src.services.user import UserRole, UserService
from src.services.workflow.domain import WorkflowRecord
from src.services.workflow.repository import WorkflowRepository

PASSWORD = "SecretPassword123"


@pytest_asyncio.fixture
async def workflow_week(db_session):
    """Workflow dengan course plan dua minggu sebagai induk konten."""
    suffix = shortuuid.uuid()[:10].lower()
    user = await UserService.from_session(db_session).create_user(
        username=f"content{suffix}",
        firstname="Dosen",
        lastname="Uji",
        email=f"content-{suffix}@itk.ac.id",
        role=UserRole.INSTRUCTOR,
        password=hash_password(PASSWORD),
    )

    rps = RPS(
        owner_id=user.id,
        file_name="rps.pdf",
        file_type="pdf",
        file_path="rps/rps.pdf",
        file_hash=hashlib.sha256(f"be-19-{suffix}".encode()).hexdigest(),
        status=RPSStatus.ANALYZED,
    )
    db_session.add(rps)
    await db_session.flush()

    workflow = await WorkflowRepository(db_session).create(
        WorkflowRecord.create(
            owner_id=user.id or "",
            rps_id=rps.id,
            progress_total=2,
        )
    )

    plan = CoursePlan(
        workflow_id=workflow.id,
        rps_id=rps.id,
        version=1,
        weeks_count=2,
        status=CoursePlanStatus.DRAFT,
    )
    db_session.add(plan)
    await db_session.flush()

    weeks = [
        CoursePlanWeek(
            course_plan_id=plan.id,
            week_number=number,
            title=f"Materi minggu {number}",
        )
        for number in (1, 2)
    ]
    db_session.add_all(weeks)
    await db_session.flush()

    return workflow, plan, weeks


def _draft(
    workflow,
    plan,
    week,
    kind: ContentKind,
    *,
    title: str | None = None,
    content_key: str | None = None,
    content_data: dict | None = None,
) -> ContentDraft:
    return ContentDraft(
        kind=kind,
        workflow_id=workflow.id or "",
        course_plan_id=plan.id or "",
        course_plan_week_id=week.id,
        week_number=week.week_number,
        title=title or f"{kind.value} minggu {week.week_number}",
        content_data=content_data or {"kind": kind.value},
        content_markdown=(
            "# Materi\n\nIsi."
            if kind is ContentKind.LEARNING_MATERIAL
            else None
        ),
        content_key=content_key,
        prompt_version=f"{kind.value.lower()}/v1",
        model_name="model-uji",
    )


@pytest.mark.asyncio
async def test_four_content_kinds_are_stored_and_read_with_validation(
    db_session, workflow_week
):
    workflow, plan, weeks = workflow_week
    repository = ContentRepository(db_session)

    stored = []
    for kind in ContentKind:
        record = await repository.create(
            _draft(workflow, plan, weeks[0], kind)
        )
        await repository.add_validation(
            record,
            status=ValidationStatus.PASSED,
            checks={"schema": "valid", "content": "valid"},
            retry_count=1,
        )
        stored.append(record)

    assert {record.kind for record in stored} == set(ContentKind)
    assert {record.content_key for record in stored} == {
        content_key_for(workflow.id, weeks[0].week_number, kind)
        for kind in ContentKind
    }

    for record in stored:
        loaded = await repository.get_by_id(record.id)

        assert loaded is not None
        assert loaded.kind is record.kind
        assert loaded.content_data == {"kind": record.kind.value}
        assert loaded.prompt_version == f"{record.kind.value.lower()}/v1"
        assert loaded.model_name == "model-uji"
        assert loaded.validation is not None
        assert loaded.validation.status is ValidationStatus.PASSED
        assert loaded.validation.retry_count == 1
        assert loaded.validation.checks == {
            "schema": "valid",
            "content": "valid",
        }
        assert loaded.validation.validated_at is not None

    listed = await repository.list_for_workflow(workflow.id or "")

    assert len(listed) == 4
    assert all(record.validation is not None for record in listed)


@pytest.mark.asyncio
async def test_second_version_does_not_change_the_first(
    db_session, workflow_week
):
    workflow, plan, weeks = workflow_week
    repository = ContentRepository(db_session)

    first = await repository.create(
        _draft(
            workflow,
            plan,
            weeks[0],
            ContentKind.LEARNING_MATERIAL,
            title="Materi versi 1",
        )
    )
    second = await repository.create(
        _draft(
            workflow,
            plan,
            weeks[0],
            ContentKind.LEARNING_MATERIAL,
            title="Materi versi 2",
            content_key=first.content_key,
        )
    )

    assert second.content_key == first.content_key
    assert second.version == first.version + 1
    assert second.id != first.id

    loaded_first = await repository.get_by_id(first.id)
    assert loaded_first is not None
    assert loaded_first.title == "Materi versi 1"
    assert loaded_first.version == 1

    latest = await repository.get_latest(first.content_key)
    assert latest is not None
    assert latest.id == second.id
    assert latest.title == "Materi versi 2"

    versions = await repository.list_versions(first.content_key)
    assert [record.version for record in versions] == [2, 1]

    # Daftar konten hanya menampilkan versi terbaru, bukan seluruh riwayat.
    listed = await repository.list_for_workflow(workflow.id or "")
    assert [record.id for record in listed] == [second.id]


@pytest.mark.asyncio
async def test_list_filters_by_week_type_and_status(
    db_session, workflow_week
):
    workflow, plan, weeks = workflow_week
    repository = ContentRepository(db_session)

    learning_material = await repository.create(
        _draft(workflow, plan, weeks[0], ContentKind.LEARNING_MATERIAL)
    )
    await repository.create(
        _draft(workflow, plan, weeks[1], ContentKind.QUIZ)
    )

    week_one = await repository.list_for_workflow(
        workflow.id or "", week_number=1
    )
    assert [record.kind for record in week_one] == [
        ContentKind.LEARNING_MATERIAL
    ]

    quizzes = await repository.list_for_workflow(
        workflow.id or "", content_type=ContentKind.QUIZ
    )
    assert [record.kind for record in quizzes] == [ContentKind.QUIZ]

    rejected = await repository.set_status(
        learning_material.id,
        ApprovalStatus.REJECTED,
        revision_notes="Tambahkan contoh.",
    )
    assert rejected is not None
    assert rejected.status is ApprovalStatus.REJECTED
    assert rejected.revision_notes == "Tambahkan contoh."

    filtered = await repository.list_for_workflow(
        workflow.id or "", status=ApprovalStatus.REJECTED
    )
    assert [record.id for record in filtered] == [learning_material.id]


@pytest.mark.asyncio
async def test_latest_validation_wins_and_keeps_findings(
    db_session, workflow_week
):
    workflow, plan, weeks = workflow_week
    repository = ContentRepository(db_session)

    record = await repository.create(
        _draft(workflow, plan, weeks[0], ContentKind.RESOURCE)
    )
    await repository.add_validation(
        record,
        status=ValidationStatus.FAILED,
        errors={"url": "tidak dapat diakses"},
        retry_count=2,
    )
    await repository.add_validation(
        record,
        status=ValidationStatus.PASSED,
        warnings={"relevance": "perlu dicek dosen"},
        retry_count=3,
    )

    loaded = await repository.get_by_id(record.id)
    assert loaded is not None
    assert loaded.validation is not None
    assert loaded.validation.status is ValidationStatus.PASSED
    assert loaded.validation.retry_count == 3
    assert loaded.validation.warnings == {
        "relevance": "perlu dicek dosen"
    }


@pytest.mark.asyncio
async def test_content_key_is_stable_per_week_and_kind(
    db_session, workflow_week
):
    workflow, plan, weeks = workflow_week
    repository = ContentRepository(db_session)

    first = await repository.create(
        _draft(workflow, plan, weeks[0], ContentKind.ASSIGNMENT)
    )
    second = await repository.create(
        _draft(workflow, plan, weeks[0], ContentKind.ASSIGNMENT)
    )
    other_week = await repository.create(
        _draft(workflow, plan, weeks[1], ContentKind.ASSIGNMENT)
    )

    assert first.content_key == second.content_key
    assert second.version == 2
    assert other_week.content_key != first.content_key
    assert other_week.version == 1
