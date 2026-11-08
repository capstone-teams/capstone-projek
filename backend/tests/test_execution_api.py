"""Test endpoint eksekusi Moodle berbasis workflow (BE-17.2).

Membuktikan acceptance criteria BE-17.2:

- eksekusi dapat dimulai, dipantau, dan diulang melalui endpoint workflow;
- detail operasi menampilkan Moodle object ID dan pesan error untuk operasi
  gagal, beserta ringkasan dan hasil read-back;
- prasyarat yang tidak terpenuhi ditolak ``INVALID_REQUEST`` dengan kode alasan;
- dosen lain dan mahasiswa tidak dapat mengakses eksekusi yang bukan miliknya;
- endpoint eksekusi terdokumentasi pada OpenAPI (diuji juga oleh
  ``test_api_contract.py``).

Runner dijalankan sungguhan dengan Moodle palsu; pekerjaan background selesai
sebelum response ASGI test dikembalikan.
"""

from __future__ import annotations

import functools
from datetime import datetime, timezone

import httpx
import pytest
import pytest_asyncio
import shortuuid

from src.main import create_app
from src.models.course_plan import CoursePlanStatus
from src.services.auth import hash_password
from src.services.auth.tokens import create_access_token
from src.services.course_plan.domain import CoursePlanDraft, CoursePlanWeekRecord
from src.services.course_plan.repository import CoursePlanRepository
from src.services.dependencies import (
    get_db_session,
    get_execution_runner,
    get_execution_service,
)
from src.services.execution.errors import MOODLE_TARGET_NOT_SET, PLAN_NOT_APPROVED
from src.services.execution.service import ExecutionService
from src.services.rps.converter import DocumentConversion, DocumentConverter
from src.services.rps.service import RPSService
from src.services.rps.storage import LocalDocumentStorage
from src.services.user import UserRole, UserService
from src.services.workflow.broker import WorkflowEventBroker
from src.services.workflow.orchestrator import run_execution_workflow
from src.services.workflow.service import WorkflowService
from tests.test_execution_orchestrator import FakeMoodle, FixedSessionFactory

PASSWORD = "SecretPassword123"
PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
MOODLE_COURSE_ID = 42

WORKFLOWS_URL = "/api/v1/workflows"


class UnusedConverter(DocumentConverter):
    name = "unused"

    @property
    def version(self) -> str:
        return "unused-1"

    async def convert(self, *, content: bytes, file_name: str) -> DocumentConversion:
        raise AssertionError("test endpoint eksekusi tidak mengonversi dokumen")


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


async def _prepare_workflow(
    session,
    owner_id: str,
    storage: LocalDocumentStorage,
    *,
    weeks: int = 2,
    approved: bool = True,
    moodle_course_id: int | None = MOODLE_COURSE_ID,
):
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
def headers(instructor_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(instructor_id)}"}


@pytest.fixture
def other_headers(other_instructor_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(other_instructor_id)}"}


@pytest.fixture
def student_headers(student_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(student_id)}"}


@pytest_asyncio.fixture
async def app(db_session, monkeypatch):
    """Aplikasi test: Moodle palsu dan session database milik test."""
    import src.services.workflow.orchestrator as orchestrator_module

    monkeypatch.setattr(
        orchestrator_module,
        "get_session_factory",
        lambda: FixedSessionFactory(db_session),
    )
    moodle = FakeMoodle()
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
    application.state.fake_moodle = moodle
    yield application
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as http_client:
        yield http_client


def _execution_url(workflow_id: str, execution_id: str | None = None) -> str:
    url = f"{WORKFLOWS_URL}/{workflow_id}/executions"
    return url if execution_id is None else f"{url}/{execution_id}"


# --- Mulai, pantau, ulangi ---------------------------------------------------


@pytest.mark.asyncio
async def test_execution_can_be_started_monitored_and_read_back(
    db_session, client, app, headers, instructor_id, storage
):
    workflow, plan = await _prepare_workflow(db_session, instructor_id, storage)

    started = await client.post(
        _execution_url(workflow.id or ""),
        headers=headers,
        json={"scope": "STRUCTURE"},
    )

    assert started.status_code == 202
    body = started.json()
    assert body["status"] == "PENDING"
    assert body["workflow_id"] == workflow.id
    assert body["course_plan_id"] == plan.id
    assert body["scope"] == "STRUCTURE"
    assert body["moodle_course_id"] == MOODLE_COURSE_ID
    assert body["summary"] == {
        "total": 2,
        "success": 0,
        "failed": 0,
        "skipped": 0,
    }
    execution_id = body["execution_id"]

    detail = await client.get(
        _execution_url(workflow.id or "", execution_id), headers=headers
    )

    assert detail.status_code == 200
    data = detail.json()
    assert data["status"] == "SUCCESS"
    assert data["summary"] == {
        "total": 2,
        "success": 2,
        "failed": 0,
        "skipped": 0,
    }
    assert data["readback"]["matches"] is True
    assert [operation["week_number"] for operation in data["operations"]] == [1, 2]
    assert [operation["moodle_object_id"] for operation in data["operations"]] == [
        "201",
        "202",
    ]
    assert all(
        operation["status"] == "SUCCESS" for operation in data["operations"]
    )

    history = await client.get(
        _execution_url(workflow.id or ""), headers=headers
    )

    assert history.status_code == 200
    assert [item["execution_id"] for item in history.json()["items"]] == [
        execution_id
    ]

    workflow_response = await client.get(
        f"{WORKFLOWS_URL}/{workflow.id}", headers=headers
    )
    assert workflow_response.json()["status"] == "RUNNING"
    assert workflow_response.json()["stage"] == "instructor_review"


@pytest.mark.asyncio
async def test_retry_reruns_only_failed_operations(
    db_session, client, app, headers, instructor_id, storage
):
    workflow, _ = await _prepare_workflow(db_session, instructor_id, storage, weeks=2)
    app.state.fake_moodle.fail_weeks = {2}

    started = await client.post(
        _execution_url(workflow.id or ""),
        headers=headers,
        json={"scope": "STRUCTURE"},
    )
    execution_id = started.json()["execution_id"]

    failed = await client.get(
        _execution_url(workflow.id or "", execution_id), headers=headers
    )
    assert failed.json()["status"] == "FAILED"
    week_two = failed.json()["operations"][1]
    assert week_two["status"] == "FAILED" and week_two["error_message"]

    app.state.fake_moodle.fail_weeks.clear()
    retried = await client.post(
        _execution_url(workflow.id or "", execution_id) + "/retry",
        headers=headers,
    )

    assert retried.status_code == 202
    assert retried.json()["status"] == "PENDING"

    detail = await client.get(
        _execution_url(workflow.id or "", execution_id), headers=headers
    )
    assert detail.json()["status"] == "SUCCESS"
    week_two = detail.json()["operations"][1]
    assert week_two["status"] == "SUCCESS"
    assert week_two["retry_count"] == 1


# --- Prasyarat ---------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("variant", "reason"),
    [
        ("plan_not_approved", PLAN_NOT_APPROVED),
        ("target_not_set", MOODLE_TARGET_NOT_SET),
    ],
)
async def test_unmet_prerequisite_is_invalid_request_with_reason(
    db_session, client, headers, instructor_id, storage, variant, reason
):
    if variant == "plan_not_approved":
        workflow, _ = await _prepare_workflow(
            db_session, instructor_id, storage, approved=False
        )
    else:
        workflow, _ = await _prepare_workflow(
            db_session, instructor_id, storage, moodle_course_id=None
        )

    response = await client.post(
        _execution_url(workflow.id or ""),
        headers=headers,
        json={"scope": "STRUCTURE"},
    )

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "INVALID_REQUEST"
    assert error["details"] == [{"field": "reason", "message": reason}]


@pytest.mark.asyncio
async def test_full_scope_is_not_available_yet(
    db_session, client, headers, instructor_id, storage
):
    workflow, _ = await _prepare_workflow(db_session, instructor_id, storage)

    response = await client.post(
        _execution_url(workflow.id or ""),
        headers=headers,
        json={"scope": "FULL"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


# --- Otorisasi ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_other_instructors_and_students_cannot_access_executions(
    db_session,
    client,
    headers,
    other_headers,
    student_headers,
    instructor_id,
    storage,
):
    workflow, _ = await _prepare_workflow(db_session, instructor_id, storage)
    started = await client.post(
        _execution_url(workflow.id or ""),
        headers=headers,
        json={"scope": "STRUCTURE"},
    )
    execution_id = started.json()["execution_id"]
    detail_url = _execution_url(workflow.id or "", execution_id)

    other_detail = await client.get(detail_url, headers=other_headers)
    other_list = await client.get(
        _execution_url(workflow.id or ""), headers=other_headers
    )
    other_retry = await client.post(detail_url + "/retry", headers=other_headers)
    student_detail = await client.get(detail_url, headers=student_headers)
    student_start = await client.post(
        _execution_url(workflow.id or ""),
        headers=student_headers,
        json={"scope": "STRUCTURE"},
    )

    assert other_detail.status_code == 404
    assert other_list.status_code == 404
    assert other_retry.status_code == 404
    assert all(
        response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
        for response in (other_detail, other_list, other_retry)
    )
    assert student_detail.status_code == 403
    assert student_start.status_code == 403
    assert student_detail.json()["error"]["code"] == "AUTHORIZATION_DENIED"
