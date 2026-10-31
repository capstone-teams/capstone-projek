"""Test endpoint RPS (BE-05) melalui ASGI app di atas PostgreSQL sungguhan.

Endpoint diuji end-to-end: authentication → authorization → validasi berkas →
penyimpanan → penjadwalan konversi → response, lalu polling status.

Database memakai fixture ``conftest.db_session`` (PostgreSQL), sehingga native
enum ``rps_status``, kolom JSONB (``source_document``), dan constraint
benar-benar terpakai.

Kontrak pemrosesan mengikuti design-api §6.3: ``POST /rps/{id}/process``
menjawab ``202`` + ``PROCESSING`` dan konversinya berjalan **setelah** response
dikirim. Runner-nya diganti runner pengganti (terikat ke session test) supaya
kontrak "request tidak menahan konversi" dapat diuji tanpa menjalankan Docling:
satu mode menyelesaikan konversinya, satu mode hanya mencatat penjadwalan.
Konversi Docling sungguhan diuji pada ``tests/test_rps_docling_converter.py``.

Cakupan utama: matriks role (design-api §22), format envelope error (§18),
kontrak response (§6.1–§6.3), janji idempotency BE-05, dan keterbacaan kegagalan
lewat polling (issue #98).
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
import shortuuid
from sqlalchemy import text

from src.config.settings import get_settings
from src.main import create_app
from src.schemas.rps import RPSDetailResponse
from src.schemas.rps_structured import RPS_SCHEMA_VERSION
from src.services.auth import hash_password
from src.services.dependencies import (
    get_db_session,
    get_rps_processing_runner,
    get_rps_service,
)
from src.services.rps.converter import (
    ConvertedTable,
    DocumentConversion,
    DocumentConverter,
)
from src.services.rps.enums import RPSStatus
from src.services.rps.errors import DocumentConversionError, RPSDomainError
from src.services.rps.service import RPSService
from src.services.rps.storage import LocalDocumentStorage
from src.services.user import UserRole, UserService

PASSWORD = "SecretPassword123"
RPS_URL = "/api/v1/rps"

PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
OTHER_PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n%%EOF\n"
SOURCE_DOCUMENT = {
    "schema_name": "DoclingDocument",
    "pages": {"1": {"page_no": 1}, "2": {"page_no": 2}},
    "texts": [{"label": "section_header", "text": "CPMK", "prov": [{"page_no": 1}]}],
    "tables": [
        {
            "label": "table",
            "prov": [{"page_no": 2}],
            "data": {"num_rows": 2, "num_cols": 2},
        }
    ],
}

# Versi skema yang **berbeda** dari yang berlaku: dipakai untuk menguji kunci
# idempotency tanpa terikat pada nomor versi saat ini.
OTHER_SCHEMA_VERSION = "1.0" if RPS_SCHEMA_VERSION != "1.0" else "3.0"

UPLOAD_RESPONSE_FIELDS = {
    "id",
    "filename",
    "status",
    "file_hash",
    "schema_version",
    "deduplicated",
}
DETAIL_RESPONSE_FIELDS = {
    "id",
    "filename",
    "status",
    "file_hash",
    "schema_version",
    "created_at",
    "updated_at",
    "has_source_document",
    "workflow_id",
    "processing_duration_ms",
    "processing_error_code",
    "processing_error_message",
}


class StubConverter(DocumentConverter):
    """Konverter palsu: hasil tetap, dapat disuruh gagal, mencatat pemanggilan.

    ``fail`` dan ``document_json`` sengaja dapat diubah setelah dibuat, sehingga
    test dapat mensimulasikan kegagalan atau hasil kosong lalu mengulang
    pemrosesan tanpa mengganti dependency aplikasi.
    """

    name = "stub"

    def __init__(self, *, fail: bool = False) -> None:
        self.document_json = SOURCE_DOCUMENT
        self.fail = fail
        self.calls = 0

    @property
    def version(self) -> str:
        return "stub-1"

    async def convert(self, *, content: bytes, file_name: str) -> DocumentConversion:
        self.calls += 1
        if self.fail:
            raise DocumentConversionError(
                "stub sengaja gagal",
                public_reason="Dokumen contoh tidak dapat dikonversi.",
            )
        return DocumentConversion(
            document_json=self.document_json,
            tables=[ConvertedTable(index=0, page=2, cells=[["a"]])],
            converter_name=self.name,
            converter_version=self.version,
        )


class ScheduledRunner:
    """Runner pengganti yang meniru :func:`src.services.rps.runner.run_rps_processing`.

    ``complete=False`` menirukan keadaan "response sudah dikirim, konversi belum
    selesai" — inilah yang membuat janji *tidak menahan request* dapat diuji.
    Kegagalan domain ditelan seperti runner asli, karena tidak ada client yang
    menunggu hasilnya.
    """

    def __init__(self, *, complete: bool, session, storage, converter) -> None:
        self.complete = complete
        self.calls: list[dict[str, str]] = []
        self._session = session
        self._storage = storage
        self._converter = converter

    async def __call__(self, *, rps_id: str, owner_id: str) -> None:
        self.calls.append({"rps_id": rps_id, "owner_id": owner_id})
        if not self.complete:
            return

        service = RPSService.from_session(
            self._session, storage=self._storage, converter=self._converter
        )
        try:
            await service.convert(rps_id=rps_id, owner_id=owner_id)
        except RPSDomainError:
            # Sudah tercatat sebagai FAILED pada dokumen; sama seperti runner asli.
            pass


@pytest.fixture
def converter() -> StubConverter:
    return StubConverter()


@pytest.fixture
def storage(tmp_path) -> LocalDocumentStorage:
    return LocalDocumentStorage(tmp_path)


@pytest.fixture
def runner(db_session, storage, converter) -> ScheduledRunner:
    return ScheduledRunner(
        complete=True, session=db_session, storage=storage, converter=converter
    )


@pytest_asyncio.fixture
async def app(db_session, storage, converter, runner) -> AsyncIterator:
    """Aplikasi dengan database test dan dependency pengganti."""
    application = create_app()

    async def override_get_db_session():
        yield db_session

    async def override_get_rps_service() -> RPSService:
        return RPSService.from_session(db_session, storage=storage, converter=converter)

    async def override_runner() -> ScheduledRunner:
        return runner

    application.dependency_overrides[get_db_session] = override_get_db_session
    application.dependency_overrides[get_rps_service] = override_get_rps_service
    application.dependency_overrides[get_rps_processing_runner] = override_runner
    yield application
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


@pytest_asyncio.fixture
async def user_service(db_session) -> UserService:
    return UserService.from_session(db_session)


async def create_user(user_service: UserService, *, email: str, role: UserRole):
    return await user_service.create_user(
        username=email.split("@")[0],
        firstname="Pengguna",
        lastname="Uji",
        email=email,
        role=role,
        password=hash_password(PASSWORD),
    )


async def login(client: httpx.AsyncClient, *, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login", json={"username": email, "password": PASSWORD}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest_asyncio.fixture
async def instructor_headers(client, user_service) -> dict[str, str]:
    await create_user(user_service, email="dosen@itk.ac.id", role=UserRole.INSTRUCTOR)
    return await login(client, email="dosen@itk.ac.id")


@pytest_asyncio.fixture
async def other_instructor_headers(client, user_service) -> dict[str, str]:
    await create_user(user_service, email="dosen2@itk.ac.id", role=UserRole.INSTRUCTOR)
    return await login(client, email="dosen2@itk.ac.id")


async def upload_rps(client, headers, *, file_name: str = "rps-basis-data.pdf", content=PDF_BYTES):
    return await client.post(
        RPS_URL,
        headers=headers,
        files={"file": (file_name, content, "application/pdf")},
    )


async def schedule_processing(client, headers, rps_id: str, **kwargs) -> httpx.Response:
    return await client.post(f"{RPS_URL}/{rps_id}/process", headers=headers, **kwargs)


async def read_detail(client, headers, rps_id: str) -> dict:
    response = await client.get(f"{RPS_URL}/{rps_id}", headers=headers)
    assert response.status_code == 200
    return response.json()


def error_code(response: httpx.Response) -> str:
    return response.json()["error"]["code"]


# --- BE-05.1: unggah dan ambil dokumen -------------------------------------


@pytest.mark.asyncio
async def test_instructor_can_upload_an_rps(client, instructor_headers):
    response = await upload_rps(client, instructor_headers)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == UPLOAD_RESPONSE_FIELDS
    assert body["filename"] == "rps-basis-data.pdf"
    assert body["status"] == "UPLOADED"
    assert body["schema_version"] == RPS_SCHEMA_VERSION
    assert body["deduplicated"] is False
    assert re.fullmatch(r"[0-9a-f]{64}", body["file_hash"])
    assert len(body["id"]) == 22


@pytest.mark.asyncio
async def test_uploaded_document_can_be_read_back(client, instructor_headers):
    uploaded = (await upload_rps(client, instructor_headers)).json()

    response = await client.get(f"{RPS_URL}/{uploaded['id']}", headers=instructor_headers)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == DETAIL_RESPONSE_FIELDS
    assert body["id"] == uploaded["id"]
    assert body["file_hash"] == uploaded["file_hash"]
    assert body["status"] == "UPLOADED"
    assert body["has_source_document"] is False
    assert body["workflow_id"] is None
    assert body["processing_duration_ms"] is None
    assert body["processing_error_code"] is None
    assert body["processing_error_message"] is None
    assert body["created_at"] and body["updated_at"]


@pytest.mark.asyncio
async def test_upload_response_does_not_leak_storage_details(client, instructor_headers):
    """Path penyimpanan adalah urusan internal (design-api §23.9)."""
    response = await upload_rps(client, instructor_headers)

    assert "file_path" not in response.text
    assert "/var/" not in response.text
    assert response.json()["filename"] == "rps-basis-data.pdf"


@pytest.mark.asyncio
async def test_reuploading_the_same_document_is_not_a_second_document(client, instructor_headers):
    """Acceptance criteria: hash dan versi skema yang sama tidak dibuat ulang."""
    first = await upload_rps(client, instructor_headers)
    second = await upload_rps(client, instructor_headers, file_name="salinan.pdf")

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["deduplicated"] is True
    assert second.json()["id"] == first.json()["id"]

    listing = await client.get(f"{RPS_URL}/{first.json()['id']}", headers=instructor_headers)
    assert listing.status_code == 200


@pytest.mark.asyncio
async def test_a_different_document_is_a_new_record(client, instructor_headers):
    first = await upload_rps(client, instructor_headers)
    second = await upload_rps(client, instructor_headers, content=OTHER_PDF)

    assert second.status_code == 201
    assert second.json()["deduplicated"] is False
    assert second.json()["id"] != first.json()["id"]


@pytest.mark.asyncio
async def test_upload_without_a_file_is_a_validation_error(client, instructor_headers):
    response = await client.post(RPS_URL, headers=instructor_headers)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_a_non_pdf_upload_is_rejected_with_invalid_file(client, instructor_headers):
    response = await upload_rps(
        client, instructor_headers, file_name="rps.docx", content=b"PK\x03\x04docx"
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "INVALID_FILE",
            "message": "File RPS tidak valid.",
            "details": [],
        }
    }


@pytest.mark.asyncio
async def test_a_file_that_only_claims_to_be_a_pdf_is_rejected(client, instructor_headers):
    response = await upload_rps(client, instructor_headers, content=b"<html>html</html>")

    assert response.status_code == 400
    assert error_code(response) == "INVALID_FILE"


@pytest.mark.asyncio
async def test_an_oversized_upload_is_rejected(client, instructor_headers, monkeypatch):
    monkeypatch.setattr(get_settings(), "RPS_MAX_UPLOAD_BYTES", 32)

    response = await upload_rps(client, instructor_headers)

    assert response.status_code == 400
    assert error_code(response) == "INVALID_FILE"


@pytest.mark.asyncio
async def test_another_instructors_document_is_not_readable(
    client, instructor_headers, other_instructor_headers
):
    uploaded = (await upload_rps(client, instructor_headers)).json()

    response = await client.get(f"{RPS_URL}/{uploaded['id']}", headers=other_instructor_headers)

    assert response.status_code == 404
    assert error_code(response) == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_an_unknown_document_is_not_found(client, instructor_headers):
    response = await client.get(f"{RPS_URL}/{shortuuid.uuid()}", headers=instructor_headers)

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "RESOURCE_NOT_FOUND",
            "message": "RPS tidak ditemukan.",
            "details": [],
        }
    }


@pytest.mark.parametrize(
    "malformed_id",
    ["bukan-id", "1234567890123456789012", "3f2504e0-4f89-41d3-9a0c-0305e82c3301"],
)
@pytest.mark.asyncio
async def test_a_malformed_identifier_is_rejected_before_the_service(
    client, instructor_headers, malformed_id
):
    response = await client.get(f"{RPS_URL}/{malformed_id}", headers=instructor_headers)

    assert response.status_code == 422


# --- BE-05.2: pemrosesan asynchronous --------------------------------------


@pytest.mark.asyncio
async def test_process_schedules_the_conversion_and_answers_202(
    client, instructor_headers, runner, converter
):
    """Acceptance criteria #98: request tidak menahan konversi."""
    uploaded = (await upload_rps(client, instructor_headers)).json()
    runner.complete = False  # konversi belum selesai saat response dikirim

    response = await schedule_processing(client, instructor_headers, uploaded["id"])

    assert response.status_code == 202
    body = response.json()
    assert set(body) == {
        "rps_id",
        "status",
        "schema_version",
        "reused",
        "workflow_id",
    }
    assert body["rps_id"] == uploaded["id"]
    assert body["status"] == "PROCESSING"
    assert body["schema_version"] == RPS_SCHEMA_VERSION
    assert body["reused"] is False
    assert len(body["workflow_id"]) == 22
    assert [call["rps_id"] for call in runner.calls] == [uploaded["id"]]
    # Konversi belum berjalan sama sekali ketika response diterima.
    assert converter.calls == 0

    detail = await read_detail(client, instructor_headers, uploaded["id"])
    assert detail["status"] == "PROCESSING"
    assert detail["workflow_id"] == body["workflow_id"]


@pytest.mark.asyncio
async def test_a_scheduled_conversion_completes_and_can_be_polled(client, instructor_headers):
    """Client memantau ``GET /rps/{id}`` sampai statusnya final."""
    uploaded = (await upload_rps(client, instructor_headers)).json()

    scheduled = await schedule_processing(client, instructor_headers, uploaded["id"])
    assert scheduled.status_code == 202

    detail = await read_detail(client, instructor_headers, uploaded["id"])
    assert detail["status"] == "PROCESSED"
    # Dokumen hasil konversi tersimpan di database (issue #98), bukan hanya di disk.
    assert detail["has_source_document"] is True
    assert detail["processing_duration_ms"] >= 1
    assert detail["processing_error_code"] is None


@pytest.mark.asyncio
async def test_the_scheduled_runner_receives_the_document_and_its_owner(
    client, instructor_headers, runner
):
    uploaded = (await upload_rps(client, instructor_headers)).json()

    await schedule_processing(client, instructor_headers, uploaded["id"])

    assert len(runner.calls) == 1
    assert runner.calls[0]["rps_id"] == uploaded["id"]
    assert len(runner.calls[0]["owner_id"]) == 22


@pytest.mark.asyncio
async def test_process_accepts_an_empty_body(client, instructor_headers):
    """Payload tidak wajib: pemrosesan default sudah bermakna."""
    uploaded = (await upload_rps(client, instructor_headers)).json()

    response = await schedule_processing(client, instructor_headers, uploaded["id"])

    assert response.status_code == 202


@pytest.mark.asyncio
async def test_processing_twice_does_not_convert_again(
    client, instructor_headers, runner, converter
):
    uploaded = (await upload_rps(client, instructor_headers)).json()

    first = await schedule_processing(client, instructor_headers, uploaded["id"])
    second = await schedule_processing(client, instructor_headers, uploaded["id"])

    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json()["reused"] is True
    assert second.json()["status"] == "PROCESSED"
    # Konversi tidak dijalankan ulang (acceptance criteria BE-05); runner tetap
    # dijadwalkan karena workflow baru masih harus menjalankan tahap analisis.
    assert converter.calls == 1
    assert first.json()["workflow_id"] != second.json()["workflow_id"]


@pytest.mark.asyncio
async def test_processing_for_a_new_schema_version_is_scheduled_again(
    client, instructor_headers, runner, converter
):
    uploaded = (await upload_rps(client, instructor_headers)).json()
    await schedule_processing(client, instructor_headers, uploaded["id"])

    response = await schedule_processing(
        client,
        instructor_headers,
        uploaded["id"],
        json={"schema_version": OTHER_SCHEMA_VERSION},
    )

    assert response.status_code == 202
    assert response.json()["schema_version"] == OTHER_SCHEMA_VERSION
    assert response.json()["reused"] is False

    detail = await read_detail(client, instructor_headers, uploaded["id"])
    assert detail["status"] == "PROCESSED"
    assert detail["schema_version"] == OTHER_SCHEMA_VERSION
    assert len(runner.calls) == 2
    assert converter.calls == 2


@pytest.mark.asyncio
async def test_a_conversion_failure_is_explained_through_polling(
    client, instructor_headers, converter
):
    """Kegagalan background harus tetap dapat dipahami client (issue #98)."""
    uploaded = (await upload_rps(client, instructor_headers)).json()
    converter.fail = True

    scheduled = await schedule_processing(client, instructor_headers, uploaded["id"])
    assert scheduled.status_code == 202  # kegagalan belum diketahui saat response

    detail = await read_detail(client, instructor_headers, uploaded["id"])
    assert detail["status"] == "FAILED"
    assert detail["processing_error_code"] == "RPS_PROCESSING_FAILED"
    assert detail["processing_error_message"]
    assert detail["has_source_document"] is False

    # Alasan yang dikembalikan aman: detail internal hanya ada di log.
    assert "stub sengaja gagal" not in detail["processing_error_message"]


@pytest.mark.asyncio
async def test_an_empty_conversion_result_is_reported_as_a_processing_failure(
    client, instructor_headers, converter
):
    """Dokumen tanpa teks yang dapat diekstrak bukan "berhasil tanpa isi"."""
    uploaded = (await upload_rps(client, instructor_headers)).json()
    converter.document_json = {
        "schema_name": "DoclingDocument",
        "texts": [],
        "tables": [],
    }

    await schedule_processing(client, instructor_headers, uploaded["id"])

    detail = await read_detail(client, instructor_headers, uploaded["id"])
    assert detail["status"] == "FAILED"
    assert detail["processing_error_code"] == "RPS_PROCESSING_FAILED"


@pytest.mark.asyncio
async def test_a_failed_document_can_be_retried_through_the_api(
    client, instructor_headers, converter
):
    uploaded = (await upload_rps(client, instructor_headers)).json()
    converter.fail = True
    await schedule_processing(client, instructor_headers, uploaded["id"])
    assert (await read_detail(client, instructor_headers, uploaded["id"]))["status"] == "FAILED"

    converter.fail = False
    retried = await schedule_processing(client, instructor_headers, uploaded["id"])

    assert retried.status_code == 202
    detail = await read_detail(client, instructor_headers, uploaded["id"])
    assert detail["status"] == "PROCESSED"
    # Catatan kegagalan sebelumnya dibersihkan oleh hasil yang berhasil.
    assert detail["processing_error_code"] is None
    assert detail["processing_error_message"] is None
    assert converter.calls == 2


@pytest.mark.asyncio
async def test_processing_a_document_twice_at_once_is_a_conflict(
    client, instructor_headers, runner
):
    """Konversi yang masih berjalan tidak boleh dijadwalkan ulang."""
    uploaded = (await upload_rps(client, instructor_headers)).json()
    runner.complete = False

    first = await schedule_processing(client, instructor_headers, uploaded["id"])
    second = await schedule_processing(client, instructor_headers, uploaded["id"])

    assert first.status_code == 202
    assert second.status_code == 409
    assert error_code(second) == "INVALID_REQUEST"
    assert len(runner.calls) == 1


@pytest.mark.asyncio
async def test_a_stuck_processing_document_can_be_reclaimed_after_the_lease(
    client, instructor_headers, runner, db_session
):
    """Konversi yang terputus (server mati) tidak boleh mengunci dokumen selamanya."""
    uploaded = (await upload_rps(client, instructor_headers)).json()
    runner.complete = False
    await schedule_processing(client, instructor_headers, uploaded["id"])

    # Tirukan pemrosesan yang berhenti di tengah jalan: barisnya sudah lama
    # tidak tersentuh, lebih tua dari batas lease.
    await db_session.execute(
        text("UPDATE rps SET updated_at = now() - interval '1 hour' WHERE id = :id"),
        {"id": uploaded["id"]},
    )
    await db_session.commit()

    response = await schedule_processing(client, instructor_headers, uploaded["id"])

    assert response.status_code == 202
    assert response.json()["status"] == "PROCESSING"
    assert len(runner.calls) == 2


@pytest.mark.asyncio
async def test_another_instructor_cannot_process_the_document(
    client, instructor_headers, other_instructor_headers, runner, converter
):
    uploaded = (await upload_rps(client, instructor_headers)).json()

    response = await schedule_processing(client, other_instructor_headers, uploaded["id"])

    assert response.status_code == 404
    assert runner.calls == []
    assert converter.calls == 0


# --- Authorization (design-api §22) ---------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path_suffix",
    [
        ("post", ""),
        ("get", "/{rps_id}"),
        ("post", "/{rps_id}/process"),
    ],
)
async def test_students_are_denied_every_rps_operation(
    client, user_service, instructor_headers, method, path_suffix
):
    await create_user(user_service, email="mhs@itk.ac.id", role=UserRole.STUDENT)
    headers = await login(client, email="mhs@itk.ac.id")
    uploaded = (await upload_rps(client, instructor_headers)).json()
    url = f"{RPS_URL}{path_suffix.format(rps_id=uploaded['id'])}"

    if method == "post" and path_suffix == "":
        response = await upload_rps(client, headers)
    else:
        response = await getattr(client, method)(url, headers=headers)

    assert response.status_code == 403
    assert error_code(response) == "AUTHORIZATION_DENIED"


@pytest.mark.asyncio
async def test_administrators_are_not_instructors(client, user_service):
    """Admin bukan pengganti instructor: upload RPS tetap instructor-only."""
    await create_user(user_service, email="admin@itk.ac.id", role=UserRole.ADMIN)
    headers = await login(client, email="admin@itk.ac.id")

    response = await upload_rps(client, headers)

    assert response.status_code == 403
    assert error_code(response) == "AUTHORIZATION_DENIED"


@pytest.mark.asyncio
async def test_unauthenticated_requests_are_denied(client, instructor_headers):
    uploaded = (await upload_rps(client, instructor_headers)).json()

    responses = [
        await upload_rps(client, {}),
        await client.get(f"{RPS_URL}/{uploaded['id']}"),
        await client.post(f"{RPS_URL}/{uploaded['id']}/process"),
    ]

    assert [response.status_code for response in responses] == [401, 401, 401]
    assert {error_code(response) for response in responses} == {"AUTHENTICATION_FAILED"}
    assert all(
        response.headers.get("www-authenticate") == "Bearer" for response in responses
    )


@pytest.mark.asyncio
async def test_authorization_runs_before_processing_is_scheduled(
    client, user_service, instructor_headers, runner
):
    """Guard harus selesai sebelum dokumen ditandai PROCESSING."""
    await create_user(user_service, email="mhs@itk.ac.id", role=UserRole.STUDENT)
    headers = await login(client, email="mhs@itk.ac.id")
    uploaded = (await upload_rps(client, instructor_headers)).json()

    denied = await schedule_processing(client, headers, uploaded["id"])

    assert denied.status_code == 403
    assert runner.calls == []
    assert (await read_detail(client, instructor_headers, uploaded["id"]))["status"] == "UPLOADED"


# --- Kontrak API -----------------------------------------------------------


def test_rps_endpoints_are_part_of_the_api_spec():
    """Endpoint terdaftar pada OpenAPI di bawah prefix versi API (design-api §4)."""
    paths = create_app().openapi()["paths"]

    assert RPS_URL in paths
    assert f"{RPS_URL}/{{rps_id}}" in paths
    assert f"{RPS_URL}/{{rps_id}}/process" in paths


def test_processing_is_documented_as_an_asynchronous_operation():
    """design-api §6.3: pemrosesan menerima 202, bukan menahan request."""
    operation = create_app().openapi()["paths"][f"{RPS_URL}/{{rps_id}}/process"]["post"]

    assert "202" in operation["responses"]


def test_detail_response_fields_match_what_the_tests_assert():
    """Menjaga daftar field pada test tetap sinkron dengan DTO-nya."""
    assert set(RPSDetailResponse.model_fields) == DETAIL_RESPONSE_FIELDS
    assert RPSStatus.PROCESSING.value == "PROCESSING"
