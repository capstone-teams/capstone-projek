"""Test endpoint generate/regenerate course plan (BE-14.3).

Membuktikan prasyarat dan perilaku HTTP tahap course planning:

- ``POST /plan`` menerima ``202``, mengklaim workflow, dan tidak dapat dijalankan
  ganda;
- hanya RPS berstatus ``ANALYZED`` yang boleh memulai perencanaan;
- ``POST /plan/regenerate`` hanya setelah versi terbaru ditolak dan meneruskan
  instruksi opsional ke runner background;
- dosen lain mendapat 404 dan mahasiswa 403.

Runner background diganti stub sehingga test tidak memanggil LLM.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import httpx
import pytest
import pytest_asyncio
import shortuuid

from src.main import create_app
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
from src.services.auth.tokens import create_access_token
from src.services.course_plan import CoursePlanService
from src.services.course_plan.repository import CoursePlanRepository
from src.services.dependencies import (
    get_course_planning_runner,
    get_db_session,
)
from src.services.user import UserRole, UserService
from src.services.workflow.broker import WorkflowEventBroker
from src.services.workflow.domain import WorkflowRecord
from src.services.workflow.repository import WorkflowRepository
from src.services.workflow.service import WorkflowService

PLANS_URL = "/api/v1/workflows/{workflow_id}/plan"
PASSWORD = "SecretPassword123"

ANALYSIS: dict = {
    "course": {"name": "Basis Data", "code": "IF2230"},
    "sub_cpmk": [{"id": "SUB-1", "description": "Menjelaskan konsep"}],
    "weeks": [{"week": 1, "week_type": "regular", "topics": ["Pengenalan"]}],
}


class StubRunner:
    """Runner background palsu; mencatat argumen yang diterima."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def __call__(self, **kwargs) -> None:
        self.calls.append(kwargs)


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


async def _create_workflow(
    session,
    owner_id: str,
    *,
    analyzed: bool = True,
) -> WorkflowRecord:
    rps = RPS(
        owner_id=owner_id,
        file_name="rps.pdf",
        file_type="pdf",
        file_path="rps/rps.pdf",
        file_hash=hashlib.sha256(b"be-14-planning-api").hexdigest(),
        schema_version="2.0",
        status=RPSStatus.ANALYZED if analyzed else RPSStatus.PROCESSED,
        structured_data=(
            RPSStructuredData.model_validate(ANALYSIS).model_dump(mode="json")
            if analyzed
            else None
        ),
        analyzed_at=datetime.now(timezone.utc) if analyzed else None,
    )
    session.add(rps)
    await session.flush()

    created = await WorkflowRepository(session).create(
        WorkflowRecord.create(owner_id=owner_id, rps_id=rps.id, progress_total=2)
    )
    return await WorkflowService.from_session(
        session, broker=WorkflowEventBroker()
    ).wait_for_review(created)


def _output() -> CoursePlanOutput:
    return CoursePlanOutput(
        course=CoursePlanCourse(title="Basis Data", code="IF2230"),
        weeks=[
            CoursePlanWeek(
                week_number=1,
                title="Pengenalan",
                learning_outcomes=["SUB-1"],
                objectives=["Memahami konsep"],
                topics=["Pengenalan"],
                teaching_methods=["Ceramah"],
                planned_activities=[CoursePlanActivityType.LEARNING_MATERIAL],
            )
        ],
    )


async def _seed_plan(session, workflow: WorkflowRecord, status=CoursePlanStatus.DRAFT):
    service = CoursePlanService.from_session(session)
    record = await service.create_version(
        workflow=workflow,
        output=_output(),
        validation_result={"passed": True, "issues": []},
    )
    if status is not CoursePlanStatus.DRAFT:
        record = await CoursePlanRepository(session).set_status(
            record.id,
            status,
            revision_notes="Minggu 1 perlu diperbaiki.",
        )
    return record


@pytest_asyncio.fixture
async def runner() -> StubRunner:
    return StubRunner()


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
async def app(db_session, runner):
    application = create_app()

    async def override_get_db_session():
        yield db_session

    application.dependency_overrides[get_db_session] = override_get_db_session
    application.dependency_overrides[get_course_planning_runner] = lambda: runner
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


async def _workflow_status(db_session, workflow: WorkflowRecord) -> str:
    loaded = await WorkflowService.from_session(
        db_session, broker=WorkflowEventBroker()
    ).get_workflow(workflow_id=workflow.id or "", owner_id=workflow.owner_id)
    return loaded.status.value


@pytest.mark.asyncio
async def test_generate_claims_the_workflow_and_schedules_the_runner(
    db_session, client, headers, workflow, runner
):
    response = await client.post(
        PLANS_URL.format(workflow_id=workflow.id), headers=headers
    )

    assert response.status_code == 202
    body = response.json()
    assert body["workflow_id"] == workflow.id
    assert body["status"] == "PLANNING_COURSE"
    assert "dijadwalkan" in body["message"]

    assert runner.calls == [
        {
            "workflow_id": workflow.id,
            "owner_id": workflow.owner_id,
            "instruction": None,
        }
    ]
    assert await _workflow_status(db_session, workflow) == "PLANNING_COURSE"


@pytest.mark.asyncio
async def test_generate_cannot_run_twice(client, headers, workflow):
    url = PLANS_URL.format(workflow_id=workflow.id)

    first = await client.post(url, headers=headers)
    second = await client.post(url, headers=headers)

    assert first.status_code == 202
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.asyncio
async def test_generate_requires_an_analyzed_rps(
    db_session, client, headers, instructor_id, runner
):
    workflow = await _create_workflow(db_session, instructor_id, analyzed=False)

    response = await client.post(
        PLANS_URL.format(workflow_id=workflow.id), headers=headers
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
    assert runner.calls == []


@pytest.mark.asyncio
async def test_generate_is_rejected_when_a_plan_already_exists(
    db_session, client, headers, workflow, runner
):
    await _seed_plan(db_session, workflow)

    response = await client.post(
        PLANS_URL.format(workflow_id=workflow.id), headers=headers
    )

    assert response.status_code == 409
    assert "regenerate" in response.json()["error"]["message"].lower()
    assert runner.calls == []


@pytest.mark.asyncio
async def test_regenerate_requires_a_rejected_version(
    db_session, client, headers, workflow, runner
):
    await _seed_plan(db_session, workflow)

    response = await client.post(
        f"{PLANS_URL.format(workflow_id=workflow.id)}/regenerate", headers=headers
    )

    assert response.status_code == 409
    assert runner.calls == []


@pytest.mark.asyncio
async def test_regenerate_forwards_the_instruction(
    db_session, client, headers, workflow, runner
):
    await _seed_plan(db_session, workflow, status=CoursePlanStatus.REJECTED)

    response = await client.post(
        f"{PLANS_URL.format(workflow_id=workflow.id)}/regenerate",
        headers=headers,
        json={"instruction": "Pindahkan topik ke minggu 3."},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "PLANNING_COURSE"
    assert runner.calls == [
        {
            "workflow_id": workflow.id,
            "owner_id": workflow.owner_id,
            "instruction": "Pindahkan topik ke minggu 3.",
        }
    ]


@pytest.mark.asyncio
async def test_regenerate_without_body_is_accepted(
    db_session, client, headers, workflow, runner
):
    await _seed_plan(db_session, workflow, status=CoursePlanStatus.REJECTED)

    response = await client.post(
        f"{PLANS_URL.format(workflow_id=workflow.id)}/regenerate", headers=headers
    )

    assert response.status_code == 202
    assert runner.calls[0]["instruction"] is None

    service = CoursePlanService.from_session(db_session)
    latest = await service.get_latest(
        workflow_id=workflow.id or "", owner_id=workflow.owner_id
    )
    assert latest.revision_notes == "Minggu 1 perlu diperbaiki."


@pytest.mark.asyncio
async def test_other_instructors_and_students_cannot_generate(
    client, headers, other_headers, student_headers, workflow
):
    url = PLANS_URL.format(workflow_id=workflow.id)

    other = await client.post(url, headers=other_headers)
    student = await client.post(url, headers=student_headers)
    anonymous = await client.post(url)

    assert other.status_code == 404
    assert other.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert student.status_code == 403
    assert student.json()["error"]["code"] == "AUTHORIZATION_DENIED"
    assert anonymous.status_code == 401
