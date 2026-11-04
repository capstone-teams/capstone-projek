"""Test penyimpanan hasil analisis RPS dan reanalyze (BE-08.2).

Dua lapis pengujian:

- **domain** (tanpa database): transisi ``PROCESSED`` → ``ANALYZING`` →
  ``ANALYZED``/``FAILED``, termasuk aturan "RPS yang sudah dianalisis tidak
  dianalisis ulang secara implisit";
- **integrasi** (PostgreSQL + ASGI): endpoint ``POST /rps/{id}/reanalyze``
  menjadwalkan analisis dari ``source_document`` (Docling tidak dijalankan lagi),
  menyimpan hasil beserta waktunya, dan mencatat kegagalan dengan alasan yang
  dapat dibaca client.

Analisis model bahasa diganti analyzer palsu, sehingga pengujian tidak memanggil
LLM dan dapat membuktikan pemanggilannya (atau ketiadaan pemanggilan) secara
langsung.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
import pytest_asyncio
import shortuuid

from src.main import create_app
from src.schemas.rps_structured import RPSStructuredData
from src.services.auth import hash_password
from src.services.dependencies import (
    get_db_session,
    get_rps_analysis_runner,
    get_rps_processing_runner,
    get_rps_service,
)
from src.services.rps.analyzer import RPSAnalyzer
from src.services.rps.converter import (
    ConvertedTable,
    DocumentConversion,
    DocumentConverter,
)
from src.services.rps.domain import RPSDocument
from src.services.rps.enums import RPSStatus
from src.services.rps.errors import (
    RPSAnalysisFailedError,
    RPSDomainError,
    RPSStateError,
    RPSValidationError,
)
from src.services.rps.repository import RPSRepository
from src.services.rps.service import RPSService
from src.services.rps.storage import LocalDocumentStorage
from src.services.user import UserRole, UserService

PASSWORD = "SecretPassword123"
RPS_URL = "/api/v1/rps"

PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"

SOURCE_DOCUMENT = {
    "schema_name": "DoclingDocument",
    "pages": {"1": {"page_no": 1}},
    "texts": [{"label": "section_header", "text": "CPMK", "prov": [{"page_no": 1}]}],
    "tables": [
        {
            "label": "table",
            "prov": [{"page_no": 1}],
            "data": {"num_rows": 2, "num_cols": 2},
        }
    ],
}

# Hasil analisis yang sah dan memuat informasi akademik.
ANALYSIS_DATA: dict[str, Any] = {
    "course": {"name": "Basis Data", "code": "IF123", "credits": 3},
    "cpmk": [{"id": "CPMK-1", "description": "Merancang basis data relasional"}],
    "weeks": [{"week": 1, "topics": ["Pengenalan Basis Data"]}],
}

OWNER_ID = shortuuid.uuid()


class StubConverter(DocumentConverter):
    """Konverter palsu yang selalu menghasilkan ``SOURCE_DOCUMENT``."""

    name = "stub"

    def __init__(self) -> None:
        self.calls = 0

    @property
    def version(self) -> str:
        return "stub-1"

    async def convert(self, *, content: bytes, file_name: str) -> DocumentConversion:
        self.calls += 1
        return DocumentConversion(
            document_json=SOURCE_DOCUMENT,
            tables=[ConvertedTable(index=0, page=1, cells=[["a"]])],
            converter_name=self.name,
            converter_version=self.version,
        )


class StubAnalyzer:
    """Analyzer palsu: hasil tetap, dapat disuruh gagal, mencatat pemanggilan."""

    def __init__(
        self,
        data: dict[str, Any] | None = None,
        failure: Exception | None = None,
    ) -> None:
        self.data = data if data is not None else ANALYSIS_DATA
        self.failure = failure
        self.calls = 0

    async def __call__(self, rps_yaml: str) -> RPSStructuredData:
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        return RPSStructuredData.model_validate(self.data)


class ScheduledProcessingRunner:
    """Menjalankan konversi langsung, meniru background runner produksi."""

    def __init__(self, *, session, storage, converter) -> None:
        self._session = session
        self._storage = storage
        self._converter = converter

    async def __call__(self, *, rps_id: str, owner_id: str) -> None:
        service = RPSService.from_session(
            self._session, storage=self._storage, converter=self._converter
        )
        try:
            await service.convert(rps_id=rps_id, owner_id=owner_id)
        except RPSDomainError:
            pass


class ScheduledAnalysisRunner:
    """Menjalankan analisis langsung, meniru background runner produksi.

    ``complete=False`` menirukan keadaan "response sudah dikirim, analisis belum
    selesai" — dipakai untuk menguji penolakan analisis ganda.
    """

    def __init__(
        self,
        *,
        complete: bool,
        session,
        storage,
        converter,
        analyzer: RPSAnalyzer,
    ) -> None:
        self.complete = complete
        self.calls: list[dict[str, str]] = []
        self._session = session
        self._storage = storage
        self._converter = converter
        self._analyzer = analyzer

    async def __call__(self, *, rps_id: str, owner_id: str) -> None:
        self.calls.append({"rps_id": rps_id, "owner_id": owner_id})
        if not self.complete:
            return

        service = RPSService.from_session(
            self._session,
            storage=self._storage,
            converter=self._converter,
            analyzer=self._analyzer,
        )
        try:
            await service.analyze(rps_id=rps_id, owner_id=owner_id)
        except RPSDomainError:
            # Sudah tercatat sebagai FAILED pada dokumen; sama seperti runner asli.
            pass


@pytest.fixture
def storage(tmp_path) -> LocalDocumentStorage:
    return LocalDocumentStorage(tmp_path)


@pytest.fixture
def converter() -> StubConverter:
    return StubConverter()


@pytest.fixture
def analyzer() -> StubAnalyzer:
    return StubAnalyzer()


@pytest.fixture
def processing_runner(db_session, storage, converter) -> ScheduledProcessingRunner:
    return ScheduledProcessingRunner(
        session=db_session, storage=storage, converter=converter
    )


@pytest.fixture
def analysis_runner(
    db_session, storage, converter, analyzer
) -> ScheduledAnalysisRunner:
    return ScheduledAnalysisRunner(
        complete=True,
        session=db_session,
        storage=storage,
        converter=converter,
        analyzer=analyzer,
    )


@pytest_asyncio.fixture
async def app(
    db_session, storage, converter, analyzer, processing_runner, analysis_runner
) -> AsyncIterator:
    """Aplikasi dengan database test dan dependency pengganti."""
    application = create_app()

    async def override_get_db_session():
        yield db_session

    async def override_get_rps_service() -> RPSService:
        return RPSService.from_session(
            db_session,
            storage=storage,
            converter=converter,
            analyzer=analyzer,
        )

    async def override_processing_runner() -> ScheduledProcessingRunner:
        return processing_runner

    async def override_analysis_runner() -> ScheduledAnalysisRunner:
        return analysis_runner

    application.dependency_overrides[get_db_session] = override_get_db_session
    application.dependency_overrides[get_rps_service] = override_get_rps_service
    application.dependency_overrides[
        get_rps_processing_runner
    ] = override_processing_runner
    application.dependency_overrides[
        get_rps_analysis_runner
    ] = override_analysis_runner
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


@pytest_asyncio.fixture
async def student_headers(client, user_service) -> dict[str, str]:
    await create_user(user_service, email="mahasiswa@student.itk.ac.id", role=UserRole.STUDENT)
    return await login(client, email="mahasiswa@student.itk.ac.id")


async def upload_rps(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    file_name: str = "rps-basis-data.pdf",
    content: bytes = PDF_BYTES,
) -> httpx.Response:
    return await client.post(
        RPS_URL,
        headers=headers,
        files={"file": (file_name, content, "application/pdf")},
    )


async def processed_rps(
    client: httpx.AsyncClient, headers: dict[str, str]
) -> str:
    """Unggah lalu proses RPS sampai ``PROCESSED``; kembalikan id-nya."""
    uploaded = (await upload_rps(client, headers)).json()
    scheduled = await client.post(f"{RPS_URL}/{uploaded['id']}/process", headers=headers)
    assert scheduled.status_code == 202

    detail = await client.get(f"{RPS_URL}/{uploaded['id']}", headers=headers)
    assert detail.json()["status"] == "PROCESSED"
    return uploaded["id"]


def error_code(response: httpx.Response) -> str:
    return response.json()["error"]["code"]


# --- Domain: transisi status analisis --------------------------------------


def _document(
    *,
    status: RPSStatus,
    source_document: dict[str, Any] | None = SOURCE_DOCUMENT,
    structured_data: dict[str, Any] | None = None,
    workflow_id: str | None = None,
) -> RPSDocument:
    return RPSDocument(
        owner_id=OWNER_ID,
        file_name="rps.pdf",
        file_type="pdf",
        file_path="owner/ab/rps.pdf",
        file_hash="a" * 64,
        status=status,
        source_document=source_document,
        structured_data=structured_data,
        workflow_id=workflow_id,
    )


def test_start_analysis_requires_a_converted_document():
    document = _document(status=RPSStatus.PROCESSED, source_document=None)

    with pytest.raises(RPSValidationError):
        document.start_analysis(workflow_id=shortuuid.uuid())


def test_start_analysis_rejects_a_document_that_is_still_processing():
    document = _document(status=RPSStatus.PROCESSING)

    with pytest.raises(RPSStateError):
        document.start_analysis(workflow_id=shortuuid.uuid())


def test_analyzed_document_is_not_reanalyzed_implicitly():
    document = _document(
        status=RPSStatus.ANALYZED,
        structured_data=ANALYSIS_DATA,
        workflow_id=shortuuid.uuid(),
    )

    with pytest.raises(RPSStateError):
        document.start_analysis(workflow_id=shortuuid.uuid())

    document.start_analysis(workflow_id=shortuuid.uuid(), allow_reanalysis=True)
    assert document.status is RPSStatus.ANALYZING


def test_start_analysis_clears_previous_failure():
    document = _document(status=RPSStatus.FAILED)
    document.processing_error_code = "LLM_GENERATION_FAILED"
    document.processing_error = "Model tidak merespons."

    document.start_analysis(workflow_id=shortuuid.uuid())

    assert document.status is RPSStatus.ANALYZING
    assert document.processing_error_code is None
    assert document.processing_error is None


def test_complete_analysis_records_data_and_analysis_time():
    document = _document(status=RPSStatus.ANALYZING)

    document.complete_analysis(ANALYSIS_DATA)

    assert document.is_analyzed
    assert document.status is RPSStatus.ANALYZED
    assert document.structured_data == ANALYSIS_DATA
    assert document.analyzed_at is not None
    assert document.analyzed_at.tzinfo is not None


def test_complete_analysis_requires_analysis_to_be_running():
    document = _document(status=RPSStatus.PROCESSED)

    with pytest.raises(RPSStateError):
        document.complete_analysis(ANALYSIS_DATA)


def test_failed_analysis_keeps_the_previous_result():
    previous = {"course": {"name": "Lama"}}
    document = _document(status=RPSStatus.ANALYZING, structured_data=previous)

    document.fail_analysis(
        error_code="LLM_GENERATION_FAILED",
        reason="Layanan model tidak merespons tepat waktu.",
    )

    assert document.status is RPSStatus.FAILED
    assert document.processing_error_code == "LLM_GENERATION_FAILED"
    assert document.processing_error == "Layanan model tidak merespons tepat waktu."
    # Data lama dipertahankan; status FAILED yang menandai bukan hasil terbaru.
    assert document.structured_data == previous


# --- Integrasi: endpoint reanalyze -----------------------------------------


async def _stored_document(db_session, rps_id: str) -> RPSDocument:
    document = await RPSRepository(db_session).get_by_id(rps_id)
    assert document is not None
    return document


@pytest.mark.asyncio
async def test_instructor_can_reanalyze_without_running_docling_again(
    client, instructor_headers, db_session, analyzer, converter
):
    rps_id = await processed_rps(client, instructor_headers)
    conversions_before = converter.calls

    response = await client.post(
        f"{RPS_URL}/{rps_id}/reanalyze", headers=instructor_headers
    )

    assert response.status_code == 202
    body = response.json()
    assert set(body) == {"rps_id", "workflow_id", "status"}
    assert body["rps_id"] == rps_id
    assert len(body["workflow_id"]) == 22
    assert body["status"] == "ANALYZING"

    # Analisis selesai di background sebelum response test kembali.
    detail = (await client.get(f"{RPS_URL}/{rps_id}", headers=instructor_headers)).json()
    assert detail["status"] == "ANALYZED"
    assert detail["processing_error_code"] is None

    stored = await _stored_document(db_session, rps_id)
    assert stored.structured_data is not None
    assert stored.structured_data["course"]["name"] == "Basis Data"
    assert stored.analyzed_at is not None
    assert stored.workflow_id == body["workflow_id"]

    # Reanalyze memakai source_document: analyzer dipanggil, Docling tidak.
    assert analyzer.calls == 1
    assert converter.calls == conversions_before


@pytest.mark.asyncio
async def test_analyzed_document_is_not_analyzed_again_implicitly(
    client, instructor_headers, db_session, analyzer
):
    rps_id = await processed_rps(client, instructor_headers)
    await client.post(f"{RPS_URL}/{rps_id}/reanalyze", headers=instructor_headers)
    assert analyzer.calls == 1

    owner_id = (await _stored_document(db_session, rps_id)).owner_id
    service = RPSService.from_session(db_session, analyzer=analyzer)
    start = await service.begin_analysis(rps_id=rps_id, owner_id=owner_id)

    assert start.scheduled is False
    assert analyzer.calls == 1
    assert start.document.status is RPSStatus.ANALYZED


@pytest.mark.asyncio
async def test_reanalyze_rejects_a_document_that_was_never_converted(
    client, instructor_headers
):
    uploaded = (await upload_rps(client, instructor_headers)).json()

    response = await client.post(
        f"{RPS_URL}/{uploaded['id']}/reanalyze", headers=instructor_headers
    )

    assert response.status_code == 422
    assert error_code(response) == "INVALID_REQUEST"


@pytest.mark.asyncio
async def test_reanalyze_a_document_owned_by_another_instructor_is_not_found(
    client, instructor_headers, other_instructor_headers
):
    rps_id = await processed_rps(client, instructor_headers)

    response = await client.post(
        f"{RPS_URL}/{rps_id}/reanalyze", headers=other_instructor_headers
    )

    assert response.status_code == 404
    assert error_code(response) == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_reanalyze_requires_an_instructor_account(client, student_headers):
    response = await client.post(
        f"{RPS_URL}/{shortuuid.uuid()}/reanalyze", headers=student_headers
    )

    assert response.status_code == 403
    assert error_code(response) == "AUTHORIZATION_DENIED"


@pytest.mark.asyncio
async def test_reanalyze_is_rejected_while_analysis_is_running(
    client, instructor_headers, analysis_runner
):
    rps_id = await processed_rps(client, instructor_headers)
    analysis_runner.complete = False

    first = await client.post(f"{RPS_URL}/{rps_id}/reanalyze", headers=instructor_headers)
    second = await client.post(f"{RPS_URL}/{rps_id}/reanalyze", headers=instructor_headers)

    assert first.status_code == 202
    assert second.status_code == 409
    assert error_code(second) == "INVALID_REQUEST"


@pytest.mark.asyncio
async def test_failed_analysis_records_a_readable_reason(
    client, instructor_headers, analyzer
):
    rps_id = await processed_rps(client, instructor_headers)
    analyzer.failure = RPSAnalysisFailedError(
        "model timeout",
        public_reason="Layanan model tidak merespons tepat waktu.",
    )

    response = await client.post(
        f"{RPS_URL}/{rps_id}/reanalyze", headers=instructor_headers
    )

    assert response.status_code == 202
    detail = (await client.get(f"{RPS_URL}/{rps_id}", headers=instructor_headers)).json()
    assert detail["status"] == "FAILED"
    assert detail["processing_error_code"] == "LLM_GENERATION_FAILED"
    assert detail["processing_error_message"] == "Layanan model tidak merespons tepat waktu."


@pytest.mark.asyncio
async def test_analysis_without_academic_content_is_a_failure(
    client, instructor_headers, analyzer
):
    rps_id = await processed_rps(client, instructor_headers)
    analyzer.data = {"course": {}, "weeks": []}

    response = await client.post(
        f"{RPS_URL}/{rps_id}/reanalyze", headers=instructor_headers
    )

    assert response.status_code == 202
    detail = (await client.get(f"{RPS_URL}/{rps_id}", headers=instructor_headers)).json()
    assert detail["status"] == "FAILED"
    assert detail["processing_error_code"] == "LLM_GENERATION_FAILED"
    assert "informasi akademik" in detail["processing_error_message"]
