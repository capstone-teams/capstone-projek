"""Test endpoint review konten hasil generation (BE-19.2).

Membuktikan acceptance criteria BE-19.2:

- konten dapat difilter per minggu, jenis, dan status, dengan ringkasan
  validasi pada setiap item;
- detail versi terbaru dan riwayat versi dapat dibaca;
- reject tanpa catatan ditolak ``INVALID_REQUEST``;
- approve pada konten yang tidak lolos validasi ditolak dengan pesan jelas;
- approve/reject menghasilkan ``WorkflowEvent`` dan hanya mengenai versi
  terbaru;
- dosen lain mendapat 404 dan mahasiswa 403.

Database memakai PostgreSQL pada fixture :func:`conftest.db_session`.
"""

from __future__ import annotations

import hashlib

import httpx
import pytest
import pytest_asyncio
import shortuuid

from src.main import create_app
from src.models.course_plan import CoursePlan, CoursePlanStatus
from src.models.course_plan_week import CoursePlanWeek
from src.models.rps import RPS, RPSStatus
from src.models.validation_result import ValidationStatus
from src.schemas.content_review import CONTENT_DETAIL_EXAMPLES, ContentDetail
from src.services.auth import hash_password
from src.services.auth.tokens import create_access_token
from src.services.content import (
    ContentDraft,
    ContentKind,
    ContentRepository,
)
from src.services.dependencies import get_db_session
from src.services.user import UserRole, UserService
from src.services.workflow.broker import WorkflowEventBroker
from src.services.workflow.domain import WorkflowRecord
from src.services.workflow.repository import WorkflowRepository
from src.services.workflow.service import WorkflowService

CONTENTS_URL = "/api/v1/workflows/{workflow_id}/contents"
PASSWORD = "SecretPassword123"


async def _create_user(session, role: UserRole, label: str) -> str:
    suffix = shortuuid.uuid()[:10].lower()
    user = await UserService.from_session(session).create_user(
        username=f"{label}{suffix}",
        firstname="Pengguna",
        lastname="Uji",
        email=f"{label}-{suffix}@itk.ac.id",
        role=role,
        password=hash_password(PASSWORD),
    )
    return user.id or ""


@pytest_asyncio.fixture
async def instructor_id(db_session) -> str:
    return await _create_user(db_session, UserRole.INSTRUCTOR, "instr")


@pytest_asyncio.fixture
async def other_instructor_id(db_session) -> str:
    return await _create_user(db_session, UserRole.INSTRUCTOR, "other")


@pytest_asyncio.fixture
async def student_id(db_session) -> str:
    return await _create_user(db_session, UserRole.STUDENT, "student")


@pytest.fixture
def headers(instructor_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(instructor_id)}"}


@pytest.fixture
def other_headers(other_instructor_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(other_instructor_id)}"}


@pytest.fixture
def student_headers(student_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(student_id)}"}


@pytest_asyncio.fixture
async def app(db_session):
    application = create_app()

    async def override_get_db_session():
        yield db_session

    application.dependency_overrides[get_db_session] = override_get_db_session
    yield application
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as http_client:
        yield http_client


@pytest_asyncio.fixture
async def workspace(db_session, instructor_id):
    """Workflow dengan course plan dua minggu sebagai induk konten."""
    suffix = shortuuid.uuid()[:10].lower()
    rps = RPS(
        owner_id=instructor_id,
        file_name="rps.pdf",
        file_type="pdf",
        file_path="rps/rps.pdf",
        file_hash=hashlib.sha256(f"be-19-2-{suffix}".encode()).hexdigest(),
        status=RPSStatus.ANALYZED,
    )
    db_session.add(rps)
    await db_session.flush()

    workflow = await WorkflowRepository(db_session).create(
        WorkflowRecord.create(
            owner_id=instructor_id, rps_id=rps.id, progress_total=2
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


async def _seed(
    db_session,
    workspace,
    *,
    week_index: int = 0,
    kind: ContentKind = ContentKind.LEARNING_MATERIAL,
    content_key: str | None = None,
    validation: ValidationStatus | None = ValidationStatus.PASSED,
):
    """Simpan satu versi konten beserta hasil validasinya (opsional)."""
    workflow, plan, weeks = workspace
    week = weeks[week_index]
    repository = ContentRepository(db_session)
    record = await repository.create(
        ContentDraft(
            kind=kind,
            workflow_id=workflow.id or "",
            course_plan_id=plan.id or "",
            course_plan_week_id=week.id,
            week_number=week.week_number,
            title=f"{kind.value} minggu {week.week_number}",
            content_data={"kind": kind.value},
            content_markdown=(
                "# Materi\n\nIsi."
                if kind is ContentKind.LEARNING_MATERIAL
                else None
            ),
            content_key=content_key,
            prompt_version=f"{kind.value.lower()}/v1",
            model_name="model-uji",
        )
    )
    if validation is not None:
        await repository.add_validation(
            record,
            status=validation,
            checks={"schema": validation.value},
            errors=None if validation is ValidationStatus.PASSED else {"schema": ["x"]},
            score=1.0 if validation is ValidationStatus.PASSED else 0.5,
        )
    return await repository.get_by_id(record.id)


async def _events(db_session, workflow: WorkflowRecord) -> list[str]:
    events = await WorkflowService.from_session(
        db_session, broker=WorkflowEventBroker()
    ).list_events(workflow_id=workflow.id or "", owner_id=workflow.owner_id)
    return [event.event for event in events]


# --- Baca -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_contents_filters_and_validation_summary(
    db_session, client, headers, workspace
):
    workflow, _plan, _weeks = workspace
    material = await _seed(db_session, workspace)
    await _seed(db_session, workspace, kind=ContentKind.QUIZ)
    await _seed(db_session, workspace, week_index=1)

    url = CONTENTS_URL.format(workflow_id=workflow.id)
    everything = await client.get(url, headers=headers)
    assert everything.status_code == 200
    items = everything.json()["items"]
    assert len(items) == 3
    assert [item["week_number"] for item in items] == [1, 1, 2]
    assert items[0]["kind"] == "LEARNING_MATERIAL"
    assert items[0]["status"] == "DRAFT"
    assert items[0]["validation"]["status"] == "PASSED"
    assert items[0]["validation"]["score"] == 1.0

    first_week = await client.get(f"{url}?week_number=1", headers=headers)
    assert len(first_week.json()["items"]) == 2

    quiz = await client.get(f"{url}?content_type=QUIZ", headers=headers)
    only_quiz = quiz.json()["items"]
    assert [item["id"] for item in only_quiz] == [
        item["id"] for item in items if item["kind"] == "QUIZ"
    ]

    unvalidated = await client.get(f"{url}?status=PENDING_REVIEW", headers=headers)
    assert unvalidated.json()["items"] == []

    detail = await client.get(f"{url}/{material.id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["content_data"] == {"kind": "LEARNING_MATERIAL"}


@pytest.mark.asyncio
async def test_contents_are_scoped_to_owner_and_instructors_only(
    db_session, client, headers, other_headers, student_headers, workspace
):
    workflow, _plan, _weeks = workspace
    record = await _seed(db_session, workspace)
    url = CONTENTS_URL.format(workflow_id=workflow.id)

    assert (await client.get(url, headers=other_headers)).status_code == 404
    forbidden = await client.get(url, headers=student_headers)
    assert forbidden.status_code == 403

    for path in (f"{url}/{record.id}", f"{url}?week_number=1"):
        denied = await client.get(path, headers=other_headers)
        assert denied.status_code == 404
        assert denied.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

    detail = await client.get(f"{url}/{shortuuid.uuid()}", headers=headers)
    assert detail.status_code == 404
    assert detail.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_version_history_and_latest_version_in_list(
    db_session, client, headers, workspace
):
    workflow, _plan, _weeks = workspace
    first = await _seed(db_session, workspace)
    second = await _seed(db_session, workspace, content_key=first.content_key)

    url = CONTENTS_URL.format(workflow_id=workflow.id)
    items = (await client.get(url, headers=headers)).json()["items"]
    assert [item["version"] for item in items] == [2]
    assert items[0]["id"] == second.id

    history = await client.get(f"{url}/{first.id}/versions", headers=headers)
    assert history.status_code == 200
    versions = history.json()["items"]
    assert [item["version"] for item in versions] == [2, 1]


# --- Approve ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_approve_by_content_id_targets_latest_version_and_writes_event(
    db_session, client, headers, workspace
):
    workflow, _plan, _weeks = workspace
    first = await _seed(db_session, workspace)
    latest = await _seed(db_session, workspace, content_key=first.content_key)

    url = CONTENTS_URL.format(workflow_id=workflow.id)
    response = await client.post(
        f"{url}/approve", headers=headers, json={"content_ids": [first.id]}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "APPROVED"
    assert [item["id"] for item in body["items"]] == [latest.id]
    assert body["items"][0]["status"] == "APPROVED"

    events = await WorkflowService.from_session(
        db_session, broker=WorkflowEventBroker()
    ).list_events(workflow_id=workflow.id or "", owner_id=workflow.owner_id)
    approved = [
        event for event in events if event.event == "WORKFLOW_CONTENTS_APPROVED"
    ]
    assert len(approved) == 1
    assert approved[0].metadata_["content_ids"] == [latest.id]

    # Permintaan berulang aman dan tidak menulis event kedua.
    again = await client.post(
        f"{url}/approve", headers=headers, json={"content_ids": [first.id]}
    )
    assert again.status_code == 200
    assert again.json()["items"][0]["status"] == "APPROVED"
    assert (await _events(db_session, workflow)).count(
        "WORKFLOW_CONTENTS_APPROVED"
    ) == 1


@pytest.mark.asyncio
async def test_approve_is_blocked_when_validation_has_not_passed(
    db_session, client, headers, workspace
):
    workflow, _plan, _weeks = workspace
    material = await _seed(db_session, workspace)
    await _seed(
        db_session,
        workspace,
        kind=ContentKind.QUIZ,
        validation=ValidationStatus.FAILED,
    )

    url = CONTENTS_URL.format(workflow_id=workflow.id)
    response = await client.post(f"{url}/approve", headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
    assert "validasi" in response.json()["error"]["message"]

    detail = await client.get(f"{url}/{material.id}", headers=headers)
    assert detail.json()["status"] == "DRAFT"
    assert "WORKFLOW_CONTENTS_APPROVED" not in await _events(db_session, workflow)


# --- Reject -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_reject_requires_notes(db_session, client, headers, workspace):
    await _seed(db_session, workspace)
    workflow, _plan, _weeks = workspace
    url = CONTENTS_URL.format(workflow_id=workflow.id)

    blank = await client.post(f"{url}/reject", headers=headers, json={"notes": "   "})
    assert blank.status_code == 422
    assert blank.json()["error"]["code"] == "INVALID_REQUEST"

    missing = await client.post(f"{url}/reject", headers=headers, json={})
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.asyncio
async def test_reject_by_week_stores_notes_and_writes_event(
    db_session, client, headers, workspace
):
    workflow, _plan, _weeks = workspace
    await _seed(db_session, workspace)
    await _seed(db_session, workspace, kind=ContentKind.QUIZ)
    other_week = await _seed(db_session, workspace, week_index=1)
    notes = "Minggu 1 perlu contoh tambahan."

    url = CONTENTS_URL.format(workflow_id=workflow.id)
    response = await client.post(
        f"{url}/reject",
        headers=headers,
        json={"week_number": 1, "notes": notes},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "REJECTED"
    assert [item["week_number"] for item in body["items"]] == [1, 1]
    assert all(item["status"] == "REJECTED" for item in body["items"])
    assert all(item["revision_notes"] == notes for item in body["items"])

    untouched = await client.get(f"{url}/{other_week.id}", headers=headers)
    assert untouched.json()["status"] == "DRAFT"

    events = await WorkflowService.from_session(
        db_session, broker=WorkflowEventBroker()
    ).list_events(workflow_id=workflow.id or "", owner_id=workflow.owner_id)
    rejected = [
        event for event in events if event.event == "WORKFLOW_CONTENTS_REJECTED"
    ]
    assert len(rejected) == 1
    assert rejected[0].metadata_["revision_notes"] == notes
    assert rejected[0].metadata_["count"] == 2

    both = await client.post(
        f"{url}/reject",
        headers=headers,
        json={"notes": notes, "week_number": 1, "content_ids": [other_week.id]},
    )
    assert both.status_code == 422
    assert both.json()["error"]["code"] == "INVALID_REQUEST"


# --- Dokumentasi ------------------------------------------------------------


@pytest.mark.asyncio
async def test_openapi_examples_validate_for_every_content_kind(app):
    assert set(CONTENT_DETAIL_EXAMPLES) == {kind.value for kind in ContentKind}
    for kind, example in CONTENT_DETAIL_EXAMPLES.items():
        validated = ContentDetail.model_validate(example["value"])
        assert validated.kind.value == kind

    paths = app.openapi()["paths"]
    response = paths["/api/v1/workflows/{workflow_id}/contents/{content_id}"]["get"]
    examples = response["responses"]["200"]["content"]["application/json"]["examples"]
    assert set(examples) == set(CONTENT_DETAIL_EXAMPLES)
