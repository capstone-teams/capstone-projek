"""Test endpoint eksekusi FULL dan verifikasi berbasis workflow (BE-22.2).

Membuktikan acceptance criteria BE-22.2 dengan Moodle tiruan
(``tests.moodle_fakes.ActivityMoodle``) dan runner sungguhan:

- ``POST /workflows/{id}/executions`` menerima ``scope: "FULL"`` dan detail
  eksekusi memuat operasi per konten (minggu, jenis, judul, status, Moodle
  object ID, pesan error) termasuk ``SKIPPED``;
- ``POST /workflows/{id}/verifications`` menjalankan verifikasi (ulang), dan
  ``GET`` daftar/detail menampilkan hasil, perbedaan, jumlah perbaikan, waktu;
- prasyarat ditolak ``INVALID_REQUEST`` dengan kode alasan;
- hanya dosen pemilik workflow yang dapat mengakses; mahasiswa 403;
- response tidak memuat credential Moodle.
"""

from __future__ import annotations

import functools

import httpx
import pytest
import pytest_asyncio

from src.main import create_app
from src.services.auth.tokens import create_access_token
from src.services.content.domain import ContentKind
from src.services.dependencies import (
    get_db_session,
    get_execution_runner,
    get_execution_service,
    get_verification_service,
)
from src.services.execution.errors import EXECUTION_IN_PROGRESS
from src.services.execution.service import ExecutionService
from src.services.moodle_client import MoodleClient
from src.services.moodle_integration_service import MoodleIntegrationService
from src.services.rps.storage import LocalDocumentStorage
from src.services.user import UserRole
from src.services.verification.errors import NO_EXECUTION_TO_VERIFY
from src.services.verification.service import VerificationService
from src.services.workflow.orchestrator import run_execution_workflow
from tests.execution_fixtures import (
    FixedSessionFactory,
    approve_content,
    assignment_data,
    create_instructor,
    enable_all_activities,
    material_data,
    prepare_structure_workflow,
    quiz_data,
    resource_data,
    semester_weeks,
)
from tests.moodle_fakes import ACTIVITY_COURSE_ID, BASE_URL, TOKEN, ActivityMoodle
from tests.test_execution_api import _create_user

WORKFLOWS_URL = "/api/v1/workflows"
CONTENT_TYPES = ["LEARNING_MATERIAL", "LEARNING_RESOURCE", "ASSIGNMENT", "QUIZ"]


@pytest.fixture
def moodle_fake() -> ActivityMoodle:
    return ActivityMoodle()


@pytest_asyncio.fixture
async def moodle(moodle_fake):
    client = MoodleClient(
        BASE_URL, TOKEN, transport=httpx.MockTransport(moodle_fake.handler)
    )
    try:
        yield MoodleIntegrationService(client)
    finally:
        await client.aclose()


@pytest_asyncio.fixture
async def app(db_session, moodle, monkeypatch):
    import src.services.workflow.orchestrator as orchestrator_module

    monkeypatch.setattr(
        orchestrator_module,
        "get_session_factory",
        lambda: FixedSessionFactory(db_session),
    )
    application = create_app()

    async def override_get_db_session():
        yield db_session

    application.dependency_overrides[get_db_session] = override_get_db_session
    application.dependency_overrides[get_execution_service] = (
        lambda: ExecutionService.from_session(db_session, moodle=moodle)
    )
    application.dependency_overrides[get_execution_runner] = (
        lambda: functools.partial(run_execution_workflow, moodle=moodle)
    )
    application.dependency_overrides[get_verification_service] = (
        lambda: VerificationService.from_session(db_session, moodle=moodle)
    )
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
async def owner(db_session, tmp_path):
    """Dosen dengan workflow 2 minggu; keempat jenis konten APPROVED di minggu 1."""
    owner_id = await create_instructor(db_session)
    workflow, plan = await prepare_structure_workflow(
        db_session,
        owner_id,
        LocalDocumentStorage(tmp_path),
        moodle_course_id=ACTIVITY_COURSE_ID,
        weeks=semester_weeks(2),
    )
    await enable_all_activities(db_session, owner_id)
    for kind, data in (
        (ContentKind.LEARNING_MATERIAL, material_data(1)),
        (ContentKind.RESOURCE, resource_data(1)),
        (ContentKind.ASSIGNMENT, assignment_data(1)),
        (ContentKind.QUIZ, quiz_data(1)),
    ):
        await approve_content(db_session, workflow.id or "", plan, kind, 1, data)
    headers = {"Authorization": f"Bearer {create_access_token(owner_id)}"}
    return owner_id, workflow.id or "", headers


def executions_url(workflow_id: str, execution_id: str | None = None) -> str:
    url = f"{WORKFLOWS_URL}/{workflow_id}/executions"
    return url if execution_id is None else f"{url}/{execution_id}"


def verifications_url(workflow_id: str, verification_id: str | None = None) -> str:
    url = f"{WORKFLOWS_URL}/{workflow_id}/verifications"
    return url if verification_id is None else f"{url}/{verification_id}"


async def run_full(client, workflow_id: str, headers) -> dict:
    started = await client.post(
        executions_url(workflow_id), headers=headers, json={"scope": "FULL"}
    )
    assert started.status_code == 202, started.text
    detail = await client.get(
        executions_url(workflow_id, started.json()["execution_id"]), headers=headers
    )
    assert detail.status_code == 200
    return detail.json()


def content_operations(detail: dict, week: int) -> dict[str, dict]:
    return {
        item["operation_type"]: item
        for item in detail["operations"]
        if item["week_number"] == week and item["operation_type"] != "SECTION"
    }


# --- Eksekusi FULL --------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_execution_is_started_and_shows_operations_per_content(
    client, owner
):
    _, workflow_id, headers = owner

    started = await client.post(
        executions_url(workflow_id), headers=headers, json={"scope": "FULL"}
    )

    assert started.status_code == 202
    assert started.json()["scope"] == "FULL"
    assert started.json()["status"] == "PENDING"
    detail = await client.get(
        executions_url(workflow_id, started.json()["execution_id"]), headers=headers
    )
    data = detail.json()
    assert data["status"] == "SUCCESS"
    assert data["scope"] == "FULL"
    assert data["summary"] == {"total": 10, "success": 6, "failed": 0, "skipped": 4}

    sections = [item for item in data["operations"] if item["operation_type"] == "SECTION"]
    assert [(item["week_number"], item["title"]) for item in sections] == [
        (1, "Materi minggu 1"),
        (2, "Materi minggu 2"),
    ]

    week_one = content_operations(data, 1)
    assert sorted(week_one) == sorted(CONTENT_TYPES)
    assert {kind: item["title"] for kind, item in week_one.items()} == {
        "LEARNING_MATERIAL": "LEARNING_MATERIAL minggu 1",
        "LEARNING_RESOURCE": "RESOURCE minggu 1",
        "ASSIGNMENT": "ASSIGNMENT minggu 1",
        "QUIZ": "QUIZ minggu 1",
    }
    for item in week_one.values():
        assert item["status"] == "SUCCESS"
        assert item["content_id"]
        assert item["moodle_object_id"]
        assert item["error_message"] is None

    week_two = content_operations(data, 2)
    assert sorted(week_two) == sorted(CONTENT_TYPES)
    for item in week_two.values():
        assert item["status"] == "SKIPPED"
        assert (item["content_id"], item["title"], item["moodle_object_id"]) == (
            None,
            None,
            None,
        )
        assert item["error_message"] == "Belum ada konten APPROVED untuk jenis ini."
    assert TOKEN not in detail.text


# --- Verifikasi -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_verification_runs_repairs_and_can_be_read_back(
    client, owner, moodle_fake
):
    _, workflow_id, headers = owner
    detail = await run_full(client, workflow_id, headers)
    page_cmid = int(content_operations(detail, 1)["LEARNING_MATERIAL"]["moodle_object_id"])

    first = await client.post(verifications_url(workflow_id), headers=headers)
    moodle_fake.delete_module(page_cmid)
    second = await client.post(
        verifications_url(workflow_id),
        headers=headers,
        json={"execution_id": detail["execution_id"]},
    )

    assert first.status_code == 201
    assert first.json()["status"] == "PASS"
    assert first.json()["matches"] is True
    assert first.json()["discrepancies"] == []
    assert first.json()["summary"]["found_activities"] == 4

    repaired = second.json()
    assert second.status_code == 201
    assert repaired["status"] == "PASS"
    assert repaired["execution_id"] == detail["execution_id"]
    assert repaired["repair_count"] == 1
    assert [(item["type"], item["target"], item["week_number"]) for item in repaired["repaired"]] == [
        ("MISSING", "LEARNING_MATERIAL", 1)
    ]
    assert repaired["verified_at"]

    listed = await client.get(verifications_url(workflow_id), headers=headers)
    one = await client.get(
        verifications_url(workflow_id, repaired["verification_id"]), headers=headers
    )

    assert listed.status_code == 200
    assert [item["verification_id"] for item in listed.json()["items"]] == [
        repaired["verification_id"],
        first.json()["verification_id"],
    ]
    assert one.status_code == 200
    assert one.json() == repaired
    for response in (first, second, listed, one):
        assert TOKEN not in response.text


@pytest.mark.asyncio
async def test_remaining_differences_are_listed_in_the_result(
    client, owner, moodle_fake
):
    _, workflow_id, headers = owner
    await run_full(client, workflow_id, headers)
    manual = moodle_fake.add_manual_module(1, "Forum diskusi dosen")

    response = await client.post(verifications_url(workflow_id), headers=headers)

    result = response.json()
    assert result["status"] == "PARTIAL"
    assert result["matches"] is False
    assert result["repair_count"] == 0
    assert result["discrepancies"] == [
        {
            "type": "UNEXPECTED",
            "label": "tidak terduga",
            "target": "ACTIVITY",
            "week_number": 1,
            "message": "Module forum 'Forum diskusi dosen' tidak berasal dari eksekusi.",
            "expected": {},
            "actual": {"title": "Forum diskusi dosen", "modname": "forum", "section": 1},
            "operation_id": None,
            "moodle_object_id": manual,
            "repairable": False,
        }
    ]


# --- Prasyarat ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verification_without_a_finished_full_execution_is_rejected(
    client, owner
):
    _, workflow_id, headers = owner

    response = await client.post(verifications_url(workflow_id), headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
    assert response.json()["error"]["details"] == [
        {"field": "reason", "message": NO_EXECUTION_TO_VERIFY}
    ]


@pytest.mark.asyncio
async def test_verification_is_rejected_while_an_execution_is_running(
    client, owner, db_session, moodle
):
    owner_id, workflow_id, headers = owner
    await run_full(client, workflow_id, headers)
    # Eksekusi kedua dibuat tetapi belum dijalankan runner (status PENDING).
    await ExecutionService.from_session(db_session, moodle=moodle).start_full(
        workflow_id=workflow_id, owner_id=owner_id
    )

    response = await client.post(verifications_url(workflow_id), headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["details"] == [
        {"field": "reason", "message": EXECUTION_IN_PROGRESS}
    ]


# --- Otorisasi ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_only_the_workflow_owner_can_use_verifications(
    client, owner, db_session
):
    _, workflow_id, headers = owner
    await run_full(client, workflow_id, headers)
    created = await client.post(verifications_url(workflow_id), headers=headers)
    verification_id = created.json()["verification_id"]
    other = {
        "Authorization": f"Bearer {create_access_token(await _create_user(db_session, UserRole.INSTRUCTOR, 'other'))}"
    }
    student = {
        "Authorization": f"Bearer {create_access_token(await _create_user(db_session, UserRole.STUDENT, 'student'))}"
    }

    other_responses = [
        await client.post(verifications_url(workflow_id), headers=other),
        await client.get(verifications_url(workflow_id), headers=other),
        await client.get(verifications_url(workflow_id, verification_id), headers=other),
    ]
    student_responses = [
        await client.post(verifications_url(workflow_id), headers=student),
        await client.get(verifications_url(workflow_id), headers=student),
        await client.get(verifications_url(workflow_id, verification_id), headers=student),
        await client.post(
            executions_url(workflow_id), headers=student, json={"scope": "FULL"}
        ),
    ]
    unknown = await client.get(
        verifications_url(workflow_id, "Vr5tY7uJ9oP2aS4dF6gHjK"), headers=headers
    )

    assert [response.status_code for response in other_responses] == [404] * 3
    assert {response.json()["error"]["code"] for response in other_responses} == {
        "RESOURCE_NOT_FOUND"
    }
    assert [response.status_code for response in student_responses] == [403] * 4
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "RESOURCE_NOT_FOUND"