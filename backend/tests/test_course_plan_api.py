"""Test endpoint review course plan (BE-14.2).

Membuktikan acceptance criteria BE-14.2:

- course plan terbaru dan seluruh versinya dapat diambil frontend;
- reject tanpa catatan ditolak ``INVALID_REQUEST``;
- approve pada versi yang tidak lolos validasi (dan pada versi yang bukan
  ``DRAFT`` terbaru) ditolak dengan pesan yang jelas;
- dosen lain mendapat 404 dan mahasiswa 403;
- approve/reject menghasilkan ``WorkflowEvent``.

Database memakai PostgreSQL pada fixture :func:`conftest.db_session`.
"""

from __future__ import annotations


import httpx
import pytest
import pytest_asyncio
import shortuuid

from src.main import create_app
from src.models.rps import RPS, RPSStatus
from src.schemas.course_plan import (
    CoursePlanActivityType,
    CoursePlanCourse,
    CoursePlanOutput,
    CoursePlanWeek,
)
from src.services.auth import hash_password
from src.services.auth.tokens import create_access_token
from src.services.course_plan import CoursePlanService
from src.services.dependencies import get_db_session
from src.services.user import UserRole, UserService
from src.services.workflow.broker import WorkflowEventBroker
from src.services.workflow.domain import WorkflowRecord
from src.services.workflow.repository import WorkflowRepository
from src.services.workflow.service import WorkflowService

PLANS_URL = "/api/v1/workflows/{workflow_id}/plan"
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


async def _create_workflow(session, owner_id: str) -> WorkflowRecord:
    rps = RPS(
        owner_id=owner_id,
        file_name="rps.pdf",
        file_type="pdf",
        file_path="rps/rps.pdf",
        file_hash=shortuuid.uuid(),
        status=RPSStatus.ANALYZED,
    )
    session.add(rps)
    await session.flush()
    return await WorkflowRepository(session).create(
        WorkflowRecord.create(owner_id=owner_id, rps_id=rps.id, progress_total=2)
    )


def _output(*, weeks: int = 2, suffix: str = "") -> CoursePlanOutput:
    return CoursePlanOutput(
        course=CoursePlanCourse(title="Basis Data", code="IF2230"),
        weeks=[
            CoursePlanWeek(
                week_number=number,
                title=f"Materi minggu {number}{suffix}",
                learning_outcomes=[f"SUB-{number}"],
                objectives=[f"Tujuan minggu {number}"],
                topics=[f"Topik {number}"],
                teaching_methods=["Ceramah"],
                planned_activities=[CoursePlanActivityType.LEARNING_MATERIAL],
            )
            for number in range(1, weeks + 1)
        ],
    )


async def _set_review_state(session, workflow: WorkflowRecord) -> WorkflowRecord:
    service = WorkflowService.from_session(
        session, broker=WorkflowEventBroker()
    )
    return await service.wait_for_review(workflow)


async def _seed_plan(
    session,
    workflow: WorkflowRecord,
    *,
    validation_passed: bool = True,
    suffix: str = "",
):
    """Buat satu versi DRAFT pada workflow yang sudah menunggu review."""
    if workflow.status.value != "WAITING_FOR_REVIEW":
        workflow = await _set_review_state(session, workflow)

    service = CoursePlanService.from_session(session)
    return await service.create_version(
        workflow=workflow,
        output=_output(suffix=suffix),
        rps_weeks={1: {"week_type": "regular"}, 2: {"week_type": "uts"}},
        validation_result={
            "passed": validation_passed,
            "issues": [] if validation_passed else [
                {"code": "SUBCPMK_MISSING", "week": 2, "message": "SUB-2 tidak ada"}
            ],
        },
        activity_configuration={"learning_material": True},
        prompt_version="course_planning/v1",
        model_name="model-uji",
    )


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
async def workflow(db_session, instructor_id) -> WorkflowRecord:
    return await _create_workflow(db_session, instructor_id)


# --- Baca -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_latest_plan_returns_weeks_and_validation(
    db_session, client, headers, workflow
):
    await _seed_plan(db_session, workflow)

    response = await client.get(
        PLANS_URL.format(workflow_id=workflow.id), headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 1
    assert body["status"] == "DRAFT"
    assert body["course"] == {"title": "Basis Data", "code": "IF2230", "description": None}
    assert [week["week_number"] for week in body["weeks"]] == [1, 2]
    assert body["weeks"][1]["week_type"] == "uts"
    assert body["weeks"][1]["rps_week"] == 2
    assert body["weeks"][0]["planned_activities"] == ["learning_material"]
    assert body["validation"] == {"passed": True, "issues": []}
    assert body["prompt_version"] == "course_planning/v1"
    assert body["approved_at"] is None


@pytest.mark.asyncio
async def test_missing_plan_returns_404(client, headers, workflow):
    response = await client.get(
        PLANS_URL.format(workflow_id=workflow.id), headers=headers
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_version_history_and_single_version_detail(
    db_session, client, headers, workflow
):
    await _seed_plan(db_session, workflow)
    second = await _seed_plan(db_session, workflow, suffix=" (revisi)")

    history = await client.get(
        f"{PLANS_URL.format(workflow_id=workflow.id)}/versions", headers=headers
    )
    assert history.status_code == 200
    items = history.json()["items"]
    assert [item["version"] for item in items] == [2, 1]
    assert all(item["status"] == "DRAFT" for item in items)

    first = await client.get(
        f"{PLANS_URL.format(workflow_id=workflow.id)}/versions/1", headers=headers
    )
    assert first.status_code == 200
    assert first.json()["weeks"][0]["title"] == "Materi minggu 1"

    assert first.json()["version"] == 1
    assert second.version == 2

    missing = await client.get(
        f"{PLANS_URL.format(workflow_id=workflow.id)}/versions/99", headers=headers
    )
    assert missing.status_code == 404

    assert first.json()["weeks"][0]["title"] != second.weeks[0].title


# --- Approve / reject -------------------------------------------------------


@pytest.mark.asyncio
async def test_approve_latest_plan_updates_status_and_writes_event(
    db_session, client, headers, workflow
):
    stored = await _seed_plan(db_session, workflow)

    response = await client.post(
        f"{PLANS_URL.format(workflow_id=workflow.id)}/approve", headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "APPROVED"
    assert body["approved_at"]

    events = await WorkflowService.from_session(
        db_session, broker=WorkflowEventBroker()
    ).list_events(workflow_id=workflow.id or "", owner_id=workflow.owner_id)
    approved = [event for event in events if event.event == "WORKFLOW_PLAN_APPROVED"]
    assert len(approved) == 1
    assert approved[0].metadata_["course_plan_id"] == stored.id
    assert approved[0].metadata_["version"] == 1

    again = await client.post(
        f"{PLANS_URL.format(workflow_id=workflow.id)}/approve", headers=headers
    )
    assert again.status_code == 409


@pytest.mark.asyncio
async def test_approve_is_blocked_when_validation_has_not_passed(
    db_session, client, headers, workflow
):
    await _seed_plan(db_session, workflow, validation_passed=False)

    response = await client.post(
        f"{PLANS_URL.format(workflow_id=workflow.id)}/approve", headers=headers
    )

    assert response.status_code == 409
    assert "validasi" in response.json()["error"]["message"]

    latest = await client.get(
        PLANS_URL.format(workflow_id=workflow.id), headers=headers
    )
    assert latest.json()["status"] == "DRAFT"


@pytest.mark.asyncio
async def test_reject_requires_notes(db_session, client, headers, workflow):
    await _seed_plan(db_session, workflow)

    response = await client.post(
        f"{PLANS_URL.format(workflow_id=workflow.id)}/reject",
        headers=headers,
        json={"notes": "   "},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"

    latest = await client.get(
        PLANS_URL.format(workflow_id=workflow.id), headers=headers
    )
    assert latest.json()["status"] == "DRAFT"


@pytest.mark.asyncio
async def test_reject_stores_notes_and_writes_event(
    db_session, client, headers, workflow
):
    await _seed_plan(db_session, workflow)
    notes = "Minggu 8 seharusnya UTS."

    response = await client.post(
        f"{PLANS_URL.format(workflow_id=workflow.id)}/reject",
        headers=headers,
        json={"notes": notes},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "REJECTED"
    assert body["revision_notes"] == notes

    events = await WorkflowService.from_session(
        db_session, broker=WorkflowEventBroker()
    ).list_events(workflow_id=workflow.id or "", owner_id=workflow.owner_id)
    rejected = [event for event in events if event.event == "WORKFLOW_PLAN_REJECTED"]
    assert len(rejected) == 1
    assert rejected[0].metadata_["revision_notes"] == notes

    approve = await client.post(
        f"{PLANS_URL.format(workflow_id=workflow.id)}/approve", headers=headers
    )
    assert approve.status_code == 409


@pytest.mark.asyncio
async def test_review_requires_a_waiting_workflow(db_session, client, headers, workflow):
    # Workflow masih QUEUED: belum ada tahap yang selesai untuk direview.
    await CoursePlanService.from_session(db_session).create_version(
        workflow=workflow,
        output=_output(),
        validation_result={"passed": True, "issues": []},
    )

    response = await client.post(
        f"{PLANS_URL.format(workflow_id=workflow.id)}/approve", headers=headers
    )

    assert response.status_code == 409
    assert "menunggu" in response.json()["error"]["message"]


# --- Authorization ----------------------------------------------------------


@pytest.mark.asyncio
async def test_other_instructors_and_students_cannot_read_a_plan(
    db_session, client, headers, other_headers, student_headers, workflow
):
    await _seed_plan(db_session, workflow)
    url = PLANS_URL.format(workflow_id=workflow.id)

    other = await client.get(url, headers=other_headers)
    student = await client.get(url, headers=student_headers)
    anonymous = await client.get(url)

    assert other.status_code == 404
    assert other.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert student.status_code == 403
    assert student.json()["error"]["code"] == "AUTHORIZATION_DENIED"
    assert anonymous.status_code == 401
