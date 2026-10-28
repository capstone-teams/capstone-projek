"""Test endpoint daftar RPS dan hasil analisis (BE-08.3).

Dokumen dibuat langsung lewat repository (bukan unggah + konversi Docling) supaya
pengujian endpoint baca tidak bergantung pada konverter maupun model bahasa.
Yang diuji adalah kontrak HTTP dan scoping akses:

- ``GET /api/v1/rps`` hanya memuat RPS milik dosen yang login;
- ``GET /api/v1/rps/{id}/analysis`` mengembalikan RPS Structured Data untuk RPS
  ``ANALYZED``, ``422 INVALID_REQUEST`` untuk yang belum dianalisis, dan
  ``404 RESOURCE_NOT_FOUND`` untuk RPS yang tidak ada/milik dosen lain;
- mahasiswa ditolak ``403 AUTHORIZATION_DENIED`` (design-api §22).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest
import pytest_asyncio
import shortuuid

from src.main import create_app
from src.schemas.rps_structured import RPS_SCHEMA_VERSION
from src.services.auth import hash_password
from src.services.dependencies import get_db_session, get_rps_service
from src.services.rps.converter import DocumentConversion, DocumentConverter
from src.services.rps.domain import RPSDocument
from src.services.rps.enums import RPSStatus
from src.services.rps.repository import RPSRepository
from src.services.rps.service import RPSService
from src.services.rps.storage import LocalDocumentStorage
from src.services.user import UserRole, UserService

PASSWORD = "SecretPassword123"
RPS_URL = "/api/v1/rps"

SOURCE_DOCUMENT = {
    "schema_name": "DoclingDocument",
    "pages": {"1": {"page_no": 1}},
    "texts": [{"label": "section_header", "text": "CPMK", "prov": [{"page_no": 1}]}],
}

ANALYSIS_DATA: dict[str, Any] = {
    "schema_version": RPS_SCHEMA_VERSION,
    "course": {"name": "Basis Data", "code": "IF123", "credits": 3},
    "cpmk": [{"id": "CPMK-1", "description": "Merancang basis data relasional"}],
    "weeks": [{"week": 1, "topics": ["Pengenalan Basis Data"]}],
}


class StubConverter(DocumentConverter):
    """Konverter yang tidak dipakai endpoint baca; hanya memenuhi konstruktor."""

    name = "stub"

    @property
    def version(self) -> str:
        return "stub-1"

    async def convert(self, *, content: bytes, file_name: str) -> DocumentConversion:
        raise AssertionError("endpoint daftar/analisis tidak boleh mengonversi dokumen")


@pytest.fixture
def storage(tmp_path) -> LocalDocumentStorage:
    return LocalDocumentStorage(tmp_path)


@pytest_asyncio.fixture
async def app(db_session, storage) -> AsyncIterator:
    application = create_app()

    async def override_get_db_session():
        yield db_session

    async def override_get_rps_service() -> RPSService:
        return RPSService.from_session(
            db_session, storage=storage, converter=StubConverter()
        )

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
async def instructor(client, user_service) -> tuple[str, dict[str, str]]:
    user = await create_user(
        user_service, email="dosen@itk.ac.id", role=UserRole.INSTRUCTOR
    )
    return user.id, await login(client, email="dosen@itk.ac.id")


@pytest_asyncio.fixture
async def other_instructor(client, user_service) -> tuple[str, dict[str, str]]:
    user = await create_user(
        user_service, email="dosen2@itk.ac.id", role=UserRole.INSTRUCTOR
    )
    return user.id, await login(client, email="dosen2@itk.ac.id")


@pytest_asyncio.fixture
async def student_headers(client, user_service) -> dict[str, str]:
    await create_user(
        user_service, email="mahasiswa@student.itk.ac.id", role=UserRole.STUDENT
    )
    return await login(client, email="mahasiswa@student.itk.ac.id")


async def create_document(
    db_session,
    *,
    owner_id: str,
    status: RPSStatus = RPSStatus.ANALYZED,
    with_analysis: bool = True,
) -> RPSDocument:
    """Buat baris RPS dengan status/hasil analisis tertentu tanpa Docling."""
    structure = ANALYSIS_DATA if with_analysis else None
    return await RPSRepository(db_session).create(
        RPSDocument(
            owner_id=owner_id,
            file_name="rps-basis-data.pdf",
            file_type="pdf",
            file_path="owner/ab/rps-basis-data.pdf",
            file_hash="a" * 64,
            status=status,
            source_document=SOURCE_DOCUMENT,
            structured_data=structure,
            analyzed_at=(
                datetime.now(timezone.utc) if structure is not None else None
            ),
            workflow_id=shortuuid.uuid() if structure is not None else None,
        )
    )


def error_code(response: httpx.Response) -> str:
    return response.json()["error"]["code"]


# --- GET /rps --------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_only_returns_the_instructors_own_rps(
    client, db_session, instructor, other_instructor
):
    owner_id, headers = instructor
    other_id, _ = other_instructor
    own = await create_document(db_session, owner_id=owner_id)
    await create_document(db_session, owner_id=other_id)

    response = await client.get(RPS_URL, headers=headers)

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["id"] for item in items] == [own.id]
    item = items[0]
    assert item["filename"] == "rps-basis-data.pdf"
    assert item["status"] == "ANALYZED"
    assert item["schema_version"] == RPS_SCHEMA_VERSION
    assert item["workflow_id"] == own.workflow_id
    assert item["has_source_document"] is True
    assert item["created_at"] and item["updated_at"]


@pytest.mark.asyncio
async def test_list_workflow_id_is_null_before_analysis(
    client, db_session, instructor
):
    owner_id, headers = instructor
    await create_document(
        db_session,
        owner_id=owner_id,
        status=RPSStatus.PROCESSED,
        with_analysis=False,
    )

    response = await client.get(RPS_URL, headers=headers)

    assert response.status_code == 200
    assert response.json()["items"][0]["workflow_id"] is None
    assert response.json()["items"][0]["status"] == "PROCESSED"


@pytest.mark.asyncio
async def test_list_requires_an_instructor_account(client, student_headers):
    response = await client.get(RPS_URL, headers=student_headers)

    assert response.status_code == 403
    assert error_code(response) == "AUTHORIZATION_DENIED"


# --- GET /rps/{id}/analysis ------------------------------------------------


@pytest.mark.asyncio
async def test_analysis_returns_structured_data_and_analysis_time(
    client, db_session, instructor
):
    owner_id, headers = instructor
    document = await create_document(db_session, owner_id=owner_id)

    response = await client.get(f"{RPS_URL}/{document.id}/analysis", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["rps_id"] == document.id
    assert body["analyzed_at"]
    assert body["data"]["schema_version"] == RPS_SCHEMA_VERSION
    assert body["data"]["course"]["name"] == "Basis Data"
    assert body["data"]["cpmk"][0]["id"] == "CPMK-1"


@pytest.mark.asyncio
async def test_unanalyzed_rps_returns_invalid_request(
    client, db_session, instructor
):
    owner_id, headers = instructor
    document = await create_document(
        db_session,
        owner_id=owner_id,
        status=RPSStatus.PROCESSED,
        with_analysis=False,
    )

    response = await client.get(f"{RPS_URL}/{document.id}/analysis", headers=headers)

    assert response.status_code == 422
    assert error_code(response) == "INVALID_REQUEST"


@pytest.mark.asyncio
async def test_analysis_of_a_missing_rps_returns_not_found(client, instructor):
    _, headers = instructor

    response = await client.get(
        f"{RPS_URL}/{shortuuid.uuid()}/analysis", headers=headers
    )

    assert response.status_code == 404
    assert error_code(response) == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_analysis_of_another_instructors_rps_returns_not_found(
    client, db_session, instructor, other_instructor
):
    _, headers = instructor
    other_id, _ = other_instructor
    document = await create_document(db_session, owner_id=other_id)

    response = await client.get(f"{RPS_URL}/{document.id}/analysis", headers=headers)

    assert response.status_code == 404
    assert error_code(response) == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_analysis_requires_an_instructor_account(
    client, db_session, instructor, student_headers
):
    owner_id, _ = instructor
    document = await create_document(db_session, owner_id=owner_id)

    response = await client.get(
        f"{RPS_URL}/{document.id}/analysis", headers=student_headers
    )

    assert response.status_code == 403
    assert error_code(response) == "AUTHORIZATION_DENIED"
