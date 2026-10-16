"""Test endpoint RPS (BE-05) melalui ASGI app di atas PostgreSQL sungguhan.

Endpoint diuji end-to-end: authentication → authorization → validasi berkas →
penyimpanan → (opsional) konversi → response. Database memakai fixture
``conftest.db_session`` (PostgreSQL), sehingga native enum ``rps_status``,
kolom ``JSONB``, dan constraint benar-benar terpakai.

Konverter diganti konverter palsu supaya suite tetap ringan dan deterministik;
konversi Docling sungguhan diuji pada ``tests/test_rps_docling_converter.py``.
Penyimpanan memakai direktori sementara, bukan ``backend/var`` milik developer.

Cakupan utama: matriks role (design-api §22), format envelope error (§18),
kontrak response (§6.1–§6.3), dan janji idempotency BE-05.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
import shortuuid

from src.config.settings import get_settings
from src.main import create_app
from src.schemas.rps_structured import RPS_SCHEMA_VERSION
from src.services.auth import hash_password
from src.services.dependencies import get_db_session, get_rps_service
from src.services.rps.converter import (
    ConvertedTable,
    DocumentConversion,
    DocumentConverter,
)
from src.services.rps.errors import DocumentConversionError
from src.services.rps.service import RPSService
from src.services.rps.storage import LocalDocumentStorage
from src.services.user import UserRole, UserService

PASSWORD = "SecretPassword123"
RPS_URL = "/api/v1/rps"

PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
OTHER_PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n%%EOF\n"
MARKDOWN = "# RPS Basis Data\n\n| Minggu | Topik |\n| --- | --- |\n| 1 | Basis data |\n"

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
    "has_source_markdown",
    "source_markdown",
}


class StubConverter(DocumentConverter):
    """Konverter palsu: hasil tetap, dapat disuruh gagal, mencatat pemanggilan.

    ``fail`` dan ``markdown`` sengaja dapat diubah setelah dibuat, sehingga test
    dapat mensimulasikan kegagalan lalu mengulang pemrosesan tanpa mengganti
    dependency aplikasi.
    """

    name = "stub"

    def __init__(self, *, markdown: str = MARKDOWN, fail: bool = False) -> None:
        self.markdown = markdown
        self.fail = fail
        self.calls = 0

    @property
    def version(self) -> str:
        return "stub-1"

    async def convert(self, *, content: bytes, file_name: str) -> DocumentConversion:
        self.calls += 1
        if self.fail:
            raise DocumentConversionError("stub sengaja gagal")
        return DocumentConversion(
            markdown=self.markdown,
            document_json={"schema_name": "DoclingDocument"},
            document_yaml="schema_name: DoclingDocument\n",
            tables=[ConvertedTable(index=0, markdown="| a |", cells=[["a"]])],
            converter_name=self.name,
            converter_version=self.version,
        )


@pytest.fixture
def converter() -> StubConverter:
    return StubConverter()


@pytest.fixture
def storage(tmp_path) -> LocalDocumentStorage:
    return LocalDocumentStorage(tmp_path)


@pytest_asyncio.fixture
async def app(db_session, storage, converter) -> AsyncIterator:
    """Aplikasi dengan database test dan konverter/penyimpanan pengganti."""
    application = create_app()

    async def override_get_db_session():
        yield db_session

    async def override_get_rps_service() -> RPSService:
        return RPSService.from_session(db_session, storage=storage, converter=converter)

    application.dependency_overrides[get_db_session] = override_get_db_session
    application.dependency_overrides[get_rps_service] = override_get_rps_service
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
    assert body["has_source_markdown"] is False
    assert body["source_markdown"] is None
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


# --- BE-05.2: pemrosesan menjadi source_markdown ---------------------------


@pytest.mark.asyncio
async def test_process_converts_the_document(client, instructor_headers, converter):
    uploaded = (await upload_rps(client, instructor_headers)).json()

    response = await client.post(
        f"{RPS_URL}/{uploaded['id']}/process", headers=instructor_headers
    )

    assert response.status_code == 200
    assert response.json() == {
        "rps_id": uploaded["id"],
        "status": "PROCESSED",
        "schema_version": RPS_SCHEMA_VERSION,
        "reused": False,
    }
    assert converter.calls == 1

    detail = await client.get(f"{RPS_URL}/{uploaded['id']}", headers=instructor_headers)
    assert detail.json()["source_markdown"] == MARKDOWN
    assert detail.json()["has_source_markdown"] is True


@pytest.mark.asyncio
async def test_process_accepts_an_empty_body(client, instructor_headers):
    """``agent_run_id``/payload tidak wajib: pemrosesan default sudah bermakna."""
    uploaded = (await upload_rps(client, instructor_headers)).json()

    response = await client.post(
        f"{RPS_URL}/{uploaded['id']}/process", headers=instructor_headers
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_processing_twice_does_not_convert_again(client, instructor_headers, converter):
    uploaded = (await upload_rps(client, instructor_headers)).json()

    first = await client.post(f"{RPS_URL}/{uploaded['id']}/process", headers=instructor_headers)
    second = await client.post(f"{RPS_URL}/{uploaded['id']}/process", headers=instructor_headers)

    assert first.json()["reused"] is False
    assert second.json()["reused"] is True
    assert second.json()["status"] == "PROCESSED"
    assert converter.calls == 1


@pytest.mark.asyncio
async def test_processing_for_a_new_schema_version_converts_again(
    client, instructor_headers, converter
):
    uploaded = (await upload_rps(client, instructor_headers)).json()
    await client.post(f"{RPS_URL}/{uploaded['id']}/process", headers=instructor_headers)

    response = await client.post(
        f"{RPS_URL}/{uploaded['id']}/process",
        headers=instructor_headers,
        json={"schema_version": "2.0"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "rps_id": uploaded["id"],
        "status": "PROCESSED",
        "schema_version": "2.0",
        "reused": False,
    }
    assert converter.calls == 2


@pytest.mark.asyncio
async def test_a_conversion_failure_is_reported_as_rps_processing_failed(
    client, instructor_headers, converter
):
    uploaded = (await upload_rps(client, instructor_headers)).json()
    converter.fail = True

    response = await client.post(
        f"{RPS_URL}/{uploaded['id']}/process", headers=instructor_headers
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "RPS_PROCESSING_FAILED",
            "message": "Pemrosesan RPS gagal.",
            "details": [],
        }
    }
    # Detail penyebab hanya dicatat server-side.
    assert "stub sengaja gagal" not in response.text

    detail = await client.get(f"{RPS_URL}/{uploaded['id']}", headers=instructor_headers)
    assert detail.json()["status"] == "FAILED"
    assert detail.json()["source_markdown"] is None


@pytest.mark.asyncio
async def test_an_empty_conversion_result_is_reported_as_a_processing_failure(
    client, instructor_headers, converter
):
    """Dokumen tanpa teks yang dapat diekstrak bukan "berhasil tanpa isi"."""
    uploaded = (await upload_rps(client, instructor_headers)).json()
    converter.markdown = "   "

    response = await client.post(
        f"{RPS_URL}/{uploaded['id']}/process", headers=instructor_headers
    )

    assert response.status_code == 500
    assert error_code(response) == "RPS_PROCESSING_FAILED"


@pytest.mark.asyncio
async def test_a_failed_document_can_be_retried_through_the_api(
    client, instructor_headers, converter
):
    uploaded = (await upload_rps(client, instructor_headers)).json()
    converter.fail = True

    failed = await client.post(f"{RPS_URL}/{uploaded['id']}/process", headers=instructor_headers)
    assert failed.status_code == 500

    converter.fail = False
    retried = await client.post(f"{RPS_URL}/{uploaded['id']}/process", headers=instructor_headers)

    assert retried.status_code == 200
    assert retried.json()["status"] == "PROCESSED"
    assert retried.json()["reused"] is False
    assert converter.calls == 2


@pytest.mark.asyncio
async def test_another_instructor_cannot_process_the_document(
    client, instructor_headers, other_instructor_headers, converter
):
    uploaded = (await upload_rps(client, instructor_headers)).json()

    response = await client.post(
        f"{RPS_URL}/{uploaded['id']}/process", headers=other_instructor_headers
    )

    assert response.status_code == 404
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


def test_rps_endpoints_are_part_of_the_api_spec():
    """Endpoint terdaftar pada OpenAPI di bawah prefix versi API (design-api §4)."""
    paths = create_app().openapi()["paths"]

    assert RPS_URL in paths
    assert f"{RPS_URL}/{{rps_id}}" in paths
    assert f"{RPS_URL}/{{rps_id}}/process" in paths
