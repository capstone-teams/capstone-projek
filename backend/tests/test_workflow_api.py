"""Test endpoint workflow dan kanal event real-time (BE-11.3).

Membuktikan acceptance criteria BE-11.3:

- daftar/detail/riwayat workflow hanya menampilkan workflow milik dosen login;
- course target Moodle dapat disimpan dan dibaca kembali;
- event perubahan status diterima klien WebSocket; riwayat event lengkap;
- dosen lain dan mahasiswa tidak dapat mengakses workflow yang bukan miliknya.

REST diuji lewat ASGI transport pada event loop test. WebSocket memakai
``TestClient`` yang menjalankan aplikasi pada loop-nya sendiri; database yang
sama dipakai lewat engine baru di dalam loop tersebut, sehingga data yang sudah
di-commit oleh fixture tetap terlihat.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

import httpx
import pytest
import pytest_asyncio
import shortuuid
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from starlette.websockets import WebSocketDisconnect

from src.main import create_app
from src.models.workflow import WorkflowStatus
from src.models.workflow_event import EventType
from src.services.auth import hash_password
from src.services.auth.tokens import create_access_token
from src.services.dependencies import get_db_session
from src.services.rps.converter import DocumentConversion, DocumentConverter
from src.services.rps.service import RPSService
from src.services.rps.storage import LocalDocumentStorage
from src.services.user import UserRole, UserService
from src.services.workflow.broker import WorkflowEventBroker, workflow_event_broker
from src.services.workflow.domain import WorkflowRecord
from src.services.workflow.service import WorkflowService

WORKFLOWS_URL = "/api/v1/workflows"
PASSWORD = "SecretPassword123"
PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/capstone",
)


class UnusedConverter(DocumentConverter):
    """Konverter yang tidak dipakai: test ini hanya mengunggah RPS."""

    name = "unused"

    @property
    def version(self) -> str:
        return "unused-1"

    async def convert(self, *, content: bytes, file_name: str) -> DocumentConversion:
        raise AssertionError("workflow API test tidak boleh mengonversi dokumen")


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
    session, owner_id: str, storage: LocalDocumentStorage, *, total: int = 2
) -> WorkflowRecord:
    """Unggah RPS milik ``owner_id`` lalu buat workflow untuknya."""
    rps_service = RPSService.from_session(session, converter=UnusedConverter())
    uploaded = await rps_service.upload_rps(
        owner_id=owner_id, file_name="rps.pdf", content=PDF_BYTES
    )
    workflow_service = WorkflowService.from_session(
        session, broker=WorkflowEventBroker()
    )
    workflow = await workflow_service.create_for_rps(
        owner_id=owner_id,
        rps_id=uploaded.document.id or "",
        total=total,
    )
    await rps_service.attach_workflow(
        rps_id=uploaded.document.id or "",
        owner_id=owner_id,
        workflow_id=workflow.id or "",
    )
    return workflow


@pytest.fixture
def storage(tmp_path) -> LocalDocumentStorage:
    return LocalDocumentStorage(tmp_path)


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
def instructor_token(instructor_id) -> str:
    return create_access_token(instructor_id)


@pytest.fixture
def other_instructor_token(other_instructor_id) -> str:
    return create_access_token(other_instructor_id)


@pytest.fixture
def student_token(student_id) -> str:
    return create_access_token(student_id)


@pytest.fixture
def headers(instructor_token) -> dict[str, str]:
    return {"Authorization": f"Bearer {instructor_token}"}


@pytest_asyncio.fixture
async def app(db_session):
    """Aplikasi dengan session database milik test (REST)."""
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


# --- REST: daftar, detail, riwayat ------------------------------------------


@pytest.mark.asyncio
async def test_list_returns_only_the_callers_workflows(
    db_session, client, headers, instructor_id, other_instructor_id, storage
):
    mine = await _create_workflow(db_session, instructor_id, storage)
    await _create_workflow(db_session, other_instructor_id, storage)

    response = await client.get(WORKFLOWS_URL, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == [mine.id]
    item = body["items"][0]
    assert item["status"] == "QUEUED"
    assert item["stage"] is None
    assert item["progress"] == {"completed": 0, "total": 2}
    assert item["rps_id"] == mine.rps_id
    assert item["created_at"] and item["updated_at"]


@pytest.mark.asyncio
async def test_detail_maps_the_running_stage_and_moodle_target(
    db_session, client, headers, instructor_id, storage
):
    workflow = await _create_workflow(db_session, instructor_id, storage)
    service = WorkflowService.from_session(
        db_session, broker=WorkflowEventBroker()
    )
    running = await service.begin_run(workflow, total=2)
    await service.begin_stage(running, status=WorkflowStatus.PROCESSING_RPS)

    response = await client.get(f"{WORKFLOWS_URL}/{workflow.id}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "RUNNING"
    assert body["stage"] == "rps_processing"
    assert body["progress"] == {"completed": 0, "total": 2}
    assert body["moodle_course_id"] is None


@pytest.mark.asyncio
async def test_other_instructors_and_students_cannot_read_a_workflow(
    db_session,
    client,
    headers,
    instructor_id,
    other_instructor_token,
    student_token,
    storage,
):
    workflow = await _create_workflow(db_session, instructor_id, storage)

    other = await client.get(
        f"{WORKFLOWS_URL}/{workflow.id}",
        headers={"Authorization": f"Bearer {other_instructor_token}"},
    )
    student = await client.get(WORKFLOWS_URL, headers={"Authorization": f"Bearer {student_token}"})
    anonymous = await client.get(f"{WORKFLOWS_URL}/{workflow.id}")

    assert other.status_code == 404
    assert other.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert student.status_code == 403
    assert student.json()["error"]["code"] == "AUTHORIZATION_DENIED"
    assert anonymous.status_code == 401


@pytest.mark.asyncio
async def test_event_history_is_oldest_first_with_the_websocket_shape(
    db_session, client, headers, instructor_id, storage
):
    workflow = await _create_workflow(db_session, instructor_id, storage)
    service = WorkflowService.from_session(
        db_session, broker=WorkflowEventBroker()
    )
    await service.record_event(
        workflow,
        event_type=EventType.PERUBAHAN_TAHAP,
        event="WORKFLOW_STARTED",
        stage=None,
        message="Workflow dimulai.",
    )
    await asyncio.sleep(0.01)
    await service.record_event(
        workflow,
        event_type=EventType.AKTIVITAS_AGENT,
        event="WORKFLOW_STAGE_PROGRESS",
        stage="rps_processing",
        message="Membaca dokumen",
        metadata={"attempt": 1},
    )

    response = await client.get(f"{WORKFLOWS_URL}/{workflow.id}/events", headers=headers)

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["event"] for item in items] == [
        "WORKFLOW_STARTED",
        "WORKFLOW_STAGE_PROGRESS",
    ]
    assert items[0]["workflow_id"] == workflow.id
    assert items[0]["timestamp"]
    assert items[1]["stage"] == "rps_processing"
    assert items[1]["progress"] == {"completed": 0, "total": 2}
    assert "metadata" not in items[1]


# --- REST: course target Moodle ---------------------------------------------


@pytest.mark.asyncio
async def test_moodle_target_can_be_set_and_cleared(
    db_session, client, headers, instructor_id, storage
):
    workflow = await _create_workflow(db_session, instructor_id, storage)

    saved = await client.put(
        f"{WORKFLOWS_URL}/{workflow.id}/moodle-target",
        headers=headers,
        json={"moodle_course_id": 42},
    )
    cleared = await client.put(
        f"{WORKFLOWS_URL}/{workflow.id}/moodle-target",
        headers=headers,
        json={"moodle_course_id": None},
    )

    assert saved.status_code == 200
    assert saved.json()["moodle_course_id"] == 42
    assert cleared.status_code == 200
    assert cleared.json()["moodle_course_id"] is None

    detail = await client.get(f"{WORKFLOWS_URL}/{workflow.id}", headers=headers)
    assert detail.json()["moodle_course_id"] is None


@pytest.mark.asyncio
async def test_moodle_target_rejects_invalid_ids_and_other_owners(
    db_session,
    client,
    headers,
    instructor_id,
    other_instructor_token,
    storage,
):
    workflow = await _create_workflow(db_session, instructor_id, storage)

    invalid = await client.put(
        f"{WORKFLOWS_URL}/{workflow.id}/moodle-target",
        headers=headers,
        json={"moodle_course_id": 0},
    )
    missing = await client.put(
        f"{WORKFLOWS_URL}/{workflow.id}/moodle-target",
        headers=headers,
        json={},
    )
    other = await client.put(
        f"{WORKFLOWS_URL}/{workflow.id}/moodle-target",
        headers={"Authorization": f"Bearer {other_instructor_token}"},
        json={"moodle_course_id": 42},
    )

    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_FAILED"
    assert missing.status_code == 422
    assert other.status_code == 404


# --- WebSocket ---------------------------------------------------------------


def _ws_app():
    """Aplikasi WebSocket dengan session baru di loop TestClient."""
    application = create_app()

    async def override_get_db_session():
        engine = create_async_engine(TEST_DATABASE_URL)
        try:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                yield session
        finally:
            await engine.dispose()

    application.dependency_overrides[get_db_session] = override_get_db_session
    return application


@pytest.mark.asyncio
async def test_websocket_delivers_events_published_for_the_workflow(
    db_session, instructor_id, instructor_token, storage
):
    workflow = await _create_workflow(db_session, instructor_id, storage)
    payload = {
        "event": "WORKFLOW_STAGE_COMPLETED",
        "workflow_id": workflow.id,
        "stage": "rps_processing",
        "progress": {"completed": 1, "total": 2},
        "message": "Tahap pemrosesan RPS selesai.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    application = _ws_app()
    with TestClient(application) as test_client:
        with test_client.websocket_connect(
            f"/api/v1/ws/workflows/{workflow.id}?token={instructor_token}"
        ) as websocket:
            async def publish():
                workflow_event_broker.publish(workflow.id or "", payload)

            test_client.portal.call(publish)
            assert websocket.receive_json() == payload


@pytest.mark.asyncio
async def test_websocket_rejects_missing_tokens_other_owners_and_students(
    db_session,
    instructor_id,
    other_instructor_token,
    student_token,
    storage,
):
    workflow = await _create_workflow(db_session, instructor_id, storage)
    application = _ws_app()

    urls = [
        f"/api/v1/ws/workflows/{workflow.id}",
        f"/api/v1/ws/workflows/{workflow.id}?token=tidak-valid",
        f"/api/v1/ws/workflows/{workflow.id}?token={other_instructor_token}",
        f"/api/v1/ws/workflows/{workflow.id}?token={student_token}",
    ]

    with TestClient(application) as test_client:
        for url in urls:
            with pytest.raises(WebSocketDisconnect):
                with test_client.websocket_connect(url):
                    pass
