"""Test runner pemrosesan background (BE-05.2, design-api §6.3).

Runner adalah tempat konversi benar-benar dijalankan, dan ia punya dua tanggung
jawab yang mudah salah:

1. **Session sendiri.** Session milik request sudah ditutup saat runner berjalan,
   sehingga runner harus membuka session baru dari session factory aplikasi.
   Diuji dengan mengganti session factory-nya dan memastikan session itulah yang
   dipakai.
2. **Tidak meledak.** Tidak ada client yang menunggu, jadi kegagalan harus
   berhenti di runner: status dokumen (``FAILED``) dan log adalah jalur
   pelaporannya. Exception yang lolos akan menjadi "Task exception was never
   retrieved" dan menghilang tanpa jejak yang berguna.

Konverter dan penyimpanan diganti versi palsu; database memakai PostgreSQL pada
fixture ``conftest.db_session``.
"""

from __future__ import annotations

import logging

import pytest
import pytest_asyncio
import shortuuid

from src.services.auth import hash_password
from src.services.rps.converter import (
    ConvertedTable,
    DocumentConversion,
    DocumentConverter,
)
from src.services.rps.enums import RPSStatus
from src.services.rps.errors import DocumentConversionError
from src.services.rps.runner import run_rps_processing
from src.services.rps.service import RPSService
from src.services.rps.storage import LocalDocumentStorage
from src.services.user import UserRole, UserService

PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
MARKDOWN = "# RPS Basis Data\n"
PASSWORD = "SecretPassword123"


class StubConverter(DocumentConverter):
    name = "stub"

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    @property
    def version(self) -> str:
        return "stub-1"

    async def convert(self, *, content: bytes, file_name: str) -> DocumentConversion:
        self.calls += 1
        if self.fail:
            raise DocumentConversionError(
                "detail internal", public_reason="Dokumen tidak dapat dibaca."
            )
        return DocumentConversion(
            markdown=MARKDOWN,
            document_json={"schema_name": "DoclingDocument"},
            document_yaml="schema_name: DoclingDocument\n",
            tables=[ConvertedTable(index=0, markdown="| a |", cells=[["a"]])],
            converter_name=self.name,
            converter_version=self.version,
        )


class _SessionScope:
    """Async context manager yang menyerahkan session yang sudah ada.

    Meniru ``async_sessionmaker()`` tanpa membuka koneksi baru, sehingga test
    dapat memakai session PostgreSQL milik fixture.
    """

    def __init__(self, session) -> None:
        self._session = session
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        return self._session

    async def __aexit__(self, *exc_info) -> bool:
        self.exited = True
        return False


class RecordingSessionFactory:
    """Session factory palsu yang mencatat berapa kali ia dipanggil."""

    def __init__(self, session) -> None:
        self._session = session
        self.scopes: list[_SessionScope] = []

    def __call__(self) -> _SessionScope:
        scope = _SessionScope(self._session)
        self.scopes.append(scope)
        return scope


@pytest_asyncio.fixture
async def owner_id(db_session) -> str:
    """Owner dokumen; ``rps.owner_id`` adalah foreign key ke ``users.id``."""
    suffix = shortuuid.uuid()[:10].lower()
    user = await UserService.from_session(db_session).create_user(
        username=f"runner{suffix}",
        firstname="Pengguna",
        lastname="Uji",
        email=f"runner-{suffix}@itk.ac.id",
        role=UserRole.INSTRUCTOR,
        password=hash_password(PASSWORD),
    )
    return user.id or ""


@pytest.fixture
def runner_env(monkeypatch, db_session, tmp_path):
    """Siapkan runner dengan session, storage, dan konverter yang dapat diamati."""
    import src.services.rps.runner as runner_module
    import src.services.rps.service as service_module

    storage = LocalDocumentStorage(tmp_path)
    converter = StubConverter()
    session_factory = RecordingSessionFactory(db_session)

    monkeypatch.setattr(runner_module, "get_session_factory", lambda: session_factory)
    monkeypatch.setattr(service_module, "get_document_storage", lambda: storage)
    monkeypatch.setattr(service_module, "get_document_converter", lambda: converter)

    return {
        "session_factory": session_factory,
        "storage": storage,
        "converter": converter,
    }


async def create_document(db_session, storage, owner_id: str) -> str:
    """Unggah satu dokumen lewat service, lalu kembalikan identifier-nya."""
    service = RPSService.from_session(
        db_session, storage=storage, converter=StubConverter()
    )
    uploaded = await service.upload_rps(
        owner_id=owner_id, file_name="rps.pdf", content=PDF_BYTES
    )
    return uploaded.document.id or ""


async def start_processing(db_session, storage, owner_id: str) -> str:
    """Tandai dokumen ``PROCESSING`` seperti yang dilakukan endpoint ``process``."""
    rps_id = await create_document(db_session, storage, owner_id)
    service = RPSService.from_session(
        db_session, storage=storage, converter=StubConverter()
    )
    await service.begin_processing(rps_id=rps_id, owner_id=owner_id)
    return rps_id


@pytest.mark.asyncio
async def test_the_runner_opens_its_own_session(runner_env, db_session, owner_id):
    """Session request sudah tertutup saat runner berjalan."""
    storage = runner_env["storage"]
    rps_id = await start_processing(db_session, storage, owner_id)

    await run_rps_processing(rps_id=rps_id, owner_id=owner_id)

    scopes = runner_env["session_factory"].scopes
    assert len(scopes) == 1
    assert scopes[0].entered and scopes[0].exited


@pytest.mark.asyncio
async def test_the_runner_completes_the_conversion(runner_env, db_session, owner_id):
    storage = runner_env["storage"]
    converter = runner_env["converter"]
    rps_id = await start_processing(db_session, storage, owner_id)

    await run_rps_processing(rps_id=rps_id, owner_id=owner_id)

    service = RPSService.from_session(db_session, storage=storage, converter=converter)
    document = await service.get_rps(rps_id=rps_id, owner_id=owner_id)
    assert document.status is RPSStatus.PROCESSED
    assert document.source_markdown == MARKDOWN
    assert document.source_document == {"schema_name": "DoclingDocument"}
    assert converter.calls == 1


@pytest.mark.asyncio
async def test_the_runner_logs_the_recorded_duration(runner_env, db_session, owner_id, caplog):
    """Durasi yang dicatat harus terlihat di log, bukan hanya di database."""
    storage = runner_env["storage"]
    rps_id = await start_processing(db_session, storage, owner_id)

    with caplog.at_level(logging.INFO, logger="src.services.rps.runner"):
        await run_rps_processing(rps_id=rps_id, owner_id=owner_id)

    assert any("selesai" in record.message and str(rps_id) in record.getMessage() for record in caplog.records)


@pytest.mark.asyncio
async def test_a_domain_failure_is_swallowed_and_recorded(runner_env, db_session, owner_id, caplog):
    """Kegagalan berhenti di runner; dokumennya yang melaporkan status FAILED."""
    storage = runner_env["storage"]
    rps_id = await start_processing(db_session, storage, owner_id)
    runner_env["converter"].fail = True

    with caplog.at_level(logging.WARNING, logger="src.services.rps.runner"):
        await run_rps_processing(rps_id=rps_id, owner_id=owner_id)  # tidak melempar

    service = RPSService.from_session(db_session, storage=storage, converter=StubConverter())
    document = await service.get_rps(rps_id=rps_id, owner_id=owner_id)
    assert document.status is RPSStatus.FAILED
    assert document.processing_error_code == "RPS_PROCESSING_FAILED"
    assert any("gagal" in record.getMessage() for record in caplog.records)


@pytest.mark.asyncio
async def test_an_unexpected_failure_never_escapes_the_runner(
    runner_env, db_session, owner_id, monkeypatch, caplog
):
    """Bug di luar error domain tidak boleh menghilang sebagai task exception."""
    storage = runner_env["storage"]
    rps_id = await start_processing(db_session, storage, owner_id)

    async def boom(*args, **kwargs):
        raise RuntimeError("bug tak terduga")

    monkeypatch.setattr(RPSService, "convert", boom)

    with caplog.at_level(logging.ERROR, logger="src.services.rps.runner"):
        await run_rps_processing(rps_id=rps_id, owner_id=owner_id)  # tidak melempar

    assert any(record.levelno == logging.ERROR for record in caplog.records)


@pytest.mark.asyncio
async def test_the_runner_releases_its_session_on_failure(runner_env, db_session, owner_id):
    storage = runner_env["storage"]
    rps_id = await start_processing(db_session, storage, owner_id)
    runner_env["converter"].fail = True

    await run_rps_processing(rps_id=rps_id, owner_id=owner_id)

    assert runner_env["session_factory"].scopes[0].exited


@pytest.mark.asyncio
async def test_the_runner_does_nothing_for_a_document_that_is_not_processing(
    runner_env, db_session, owner_id
):
    """Runner hanya melanjutkan pekerjaan yang memang sudah dijadwalkan."""
    storage = runner_env["storage"]
    rps_id = await create_document(db_session, storage, owner_id)  # masih UPLOADED
    converter = runner_env["converter"]

    await run_rps_processing(rps_id=rps_id, owner_id=owner_id)

    assert converter.calls == 0
    service = RPSService.from_session(db_session, storage=storage, converter=converter)
    document = await service.get_rps(rps_id=rps_id, owner_id=owner_id)
    assert document.status is RPSStatus.UPLOADED
