"""Integration test BE-22.2: eksekusi FULL dan verifikasi lewat endpoint (opt-in).

Jalankan dengan ``MOODLE_LIVE_TESTS=1``. Berbeda dengan test unit, endpoint di
sini memakai dependency bawaan aplikasi: client Moodle dari konfigurasi, runner
eksekusi sungguhan, dan Verification Service sungguhan. Yang dibuktikan:

- ``POST /workflows/{id}/executions`` dengan ``scope: "FULL"`` membuat section
  dan keempat jenis activity, dan detail eksekusi menampilkan operasi per
  konten termasuk ``SKIPPED``;
- ``POST /workflows/{id}/verifications`` menghasilkan ``PASS``;
- page yang dihapus manual terdeteksi, dibuat ulang, dan hasilnya dapat dibaca
  lewat ``GET`` daftar dan detail verifikasi.

Langkah terakhir butuh ``core_course_delete_modules`` pada service web (guide
bagian 7.1, function 29); tanpa function itu test berhenti dengan skip setelah
verifikasi pertama.
"""

import os
import uuid

import httpx
import pytest
import pytest_asyncio

from src.config.settings import settings
from src.main import create_app
from src.services.auth.tokens import create_access_token
from src.services.content.domain import ContentKind
from src.services.dependencies import get_db_session
from src.services.moodle_client import MoodleClient
from src.services.moodle_exceptions import MoodlePermissionError
from src.services.moodle_integration_service import MoodleIntegrationService
from src.services.rps.storage import LocalDocumentStorage
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

pytestmark = pytest.mark.skipif(
    os.getenv("MOODLE_LIVE_TESTS") != "1",
    reason="Set MOODLE_LIVE_TESTS=1 untuk menjalankan test terhadap Moodle yang sedang menyala",
)

CONTENT_TYPES = {"LEARNING_MATERIAL", "LEARNING_RESOURCE", "ASSIGNMENT", "QUIZ"}


@pytest_asyncio.fixture
async def moodle():
    client = MoodleClient.from_settings(settings)
    try:
        yield MoodleIntegrationService(client)
    finally:
        await client.aclose()


@pytest_asyncio.fixture
async def client(db_session, monkeypatch):
    """Aplikasi dengan dependency bawaan; hanya session database yang diganti."""
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
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver", timeout=120
    ) as http_client:
        yield http_client
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def workflow(db_session, tmp_path, moodle):
    """Course baru dan workflow 2 minggu; keempat jenis konten APPROVED di minggu 1."""
    course = await moodle.create_course(
        "Execution API Test", f"api-{uuid.uuid4().hex[:8]}", 1
    )
    owner_id = await create_instructor(db_session)
    record, plan = await prepare_structure_workflow(
        db_session,
        owner_id,
        LocalDocumentStorage(tmp_path),
        moodle_course_id=course.moodle_course_id,
        weeks=semester_weeks(2),
    )
    await enable_all_activities(db_session, owner_id)
    for kind, data in (
        (ContentKind.LEARNING_MATERIAL, material_data(1)),
        (ContentKind.RESOURCE, resource_data(1)),
        (ContentKind.ASSIGNMENT, assignment_data(1)),
        (ContentKind.QUIZ, quiz_data(1)),
    ):
        await approve_content(db_session, record.id or "", plan, kind, 1, data)
    headers = {"Authorization": f"Bearer {create_access_token(owner_id)}"}
    return record.id or "", headers


@pytest.mark.asyncio
async def test_full_execution_and_verification_through_the_endpoints(
    client, moodle, workflow
):
    workflow_id, headers = workflow
    base = f"/api/v1/workflows/{workflow_id}"

    started = await client.post(
        f"{base}/executions", headers=headers, json={"scope": "FULL"}
    )
    assert started.status_code == 202, started.text
    detail = await client.get(
        f"{base}/executions/{started.json()['execution_id']}", headers=headers
    )
    execution = detail.json()
    assert execution["status"] == "SUCCESS", execution
    week_one = {
        item["operation_type"]: item
        for item in execution["operations"]
        if item["week_number"] == 1 and item["operation_type"] != "SECTION"
    }
    week_two = [
        item
        for item in execution["operations"]
        if item["week_number"] == 2 and item["operation_type"] != "SECTION"
    ]
    assert set(week_one) == CONTENT_TYPES
    assert all(
        item["status"] == "SUCCESS" and item["title"] and item["moodle_object_id"]
        for item in week_one.values()
    ), week_one
    assert {item["status"] for item in week_two} == {"SKIPPED"}

    first = await client.post(f"{base}/verifications", headers=headers)
    assert first.status_code == 201, first.text
    assert first.json()["status"] == "PASS", first.json()
    assert first.json()["summary"]["found_activities"] == 4

    page_cmid = int(week_one["LEARNING_MATERIAL"]["moodle_object_id"])
    try:
        await moodle.client.call("core_course_delete_modules", {"cmids": [page_cmid]})
    except MoodlePermissionError:
        pytest.skip(
            "Tambahkan core_course_delete_modules ke service untuk langkah ini (guide bagian 7.1, function 29)"
        )
    repaired = await client.post(f"{base}/verifications", headers=headers)
    listed = await client.get(f"{base}/verifications", headers=headers)
    one = await client.get(
        f"{base}/verifications/{repaired.json()['verification_id']}", headers=headers
    )

    result = repaired.json()
    assert result["status"] == "PASS", result
    assert result["repair_count"] == 1
    assert [(item["type"], item["target"]) for item in result["repaired"]] == [
        ("MISSING", "LEARNING_MATERIAL")
    ]
    assert [item["verification_id"] for item in listed.json()["items"]] == [
        result["verification_id"],
        first.json()["verification_id"],
    ]
    assert one.json() == result
    token = settings.MOODLE_WEB_SERVICE_TOKEN or ""
    for response in (detail, first, repaired, listed, one):
        assert not token or token not in response.text