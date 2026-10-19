"""Test script proses ulang RPS format lama (BE-13).

Script memilih baris ``PROCESSED`` yang belum memiliki ``source_document``
(format Markdown sebelum BE-13) dan menjalankan pipeline konversi saat ini.
Docling dan penyimpanan diganti service palsu; database memakai PostgreSQL pada
fixture ``conftest.db_session``.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
import shortuuid

from scripts.reprocess_rps import reprocess_legacy_rps
from src.models.rps import RPS as RPSEntity
from src.services.auth import hash_password
from src.services.rps.enums import RPSStatus
from src.services.rps.errors import DocumentConversionError
from src.services.user import UserRole, UserService

PASSWORD = "SecretPassword123"

SOURCE_DOCUMENT = {
    "schema_name": "DoclingDocument",
    "pages": {"1": {"page_no": 1}},
    "texts": [{"text": "CPMK", "prov": [{"page_no": 1}]}],
}


@asynccontextmanager
async def session_scope(session):
    """Session factory palsu: menyerahkan session fixture yang sudah ada."""
    yield session


class RecordingService:
    """Service palsu yang mencatat dokumen yang diproses ulang."""

    def __init__(self, calls: list[tuple[str, str]]) -> None:
        self._calls = calls

    async def process_rps(
        self, *, rps_id: str, owner_id: str, schema_version: str | None = None
    ) -> None:
        self._calls.append((rps_id, owner_id))


class FailingService:
    """Service palsu yang selalu gagal dengan alasan publik."""

    async def process_rps(
        self, *, rps_id: str, owner_id: str, schema_version: str | None = None
    ) -> None:
        raise DocumentConversionError(
            "detail internal", public_reason="Dokumen tidak dapat dibaca."
        )


@pytest_asyncio.fixture
async def owner_id(db_session) -> str:
    suffix = shortuuid.uuid()[:10].lower()
    user = await UserService.from_session(db_session).create_user(
        username=f"reprocess{suffix}",
        firstname="Pengguna",
        lastname="Uji",
        email=f"reprocess-{suffix}@itk.ac.id",
        role=UserRole.INSTRUCTOR,
        password=hash_password(PASSWORD),
    )
    return user.id or ""


async def create_row(
    db_session,
    owner_id: str,
    *,
    status: RPSStatus,
    source_document: dict | None,
) -> str:
    """Buat baris RPS langsung pada tabel (mensimulasikan data lama)."""
    entity = RPSEntity(
        owner_id=owner_id,
        file_name="rps-basis-data.pdf",
        file_type="PDF",
        file_path=f"{owner_id}/ab/{shortuuid.uuid()}.pdf",
        file_hash=shortuuid.uuid().encode().hex().ljust(64, "0")[:64],
        schema_version="2.0",
        status=status,
        source_document=source_document,
    )
    db_session.add(entity)
    await db_session.commit()
    await db_session.refresh(entity)
    return entity.id


@pytest.mark.asyncio
async def test_dry_run_only_counts_legacy_rows(db_session, owner_id):
    legacy_id = await create_row(
        db_session, owner_id, status=RPSStatus.PROCESSED, source_document=None
    )
    await create_row(
        db_session,
        owner_id,
        status=RPSStatus.PROCESSED,
        source_document=SOURCE_DOCUMENT,
    )
    await create_row(
        db_session, owner_id, status=RPSStatus.FAILED, source_document=None
    )

    calls: list[tuple[str, str]] = []
    report = await reprocess_legacy_rps(
        dry_run=True,
        session_factory=lambda: session_scope(db_session),
        service_factory=lambda _session: RecordingService(calls),
    )

    assert report.selected == 1
    assert report.processed == 0
    assert report.failed == 0
    assert calls == []
    assert legacy_id  # baris lama memang ada


@pytest.mark.asyncio
async def test_a_legacy_row_is_reprocessed_with_the_current_pipeline(db_session, owner_id):
    legacy_id = await create_row(
        db_session, owner_id, status=RPSStatus.PROCESSED, source_document=None
    )

    calls: list[tuple[str, str]] = []
    report = await reprocess_legacy_rps(
        session_factory=lambda: session_scope(db_session),
        service_factory=lambda _session: RecordingService(calls),
    )

    assert report.selected == 1
    assert report.processed == 1
    assert report.failed == 0
    assert calls == [(legacy_id, owner_id)]
    assert report.exit_code == 0


@pytest.mark.asyncio
async def test_failures_are_reported_without_stopping_the_run(db_session, owner_id):
    first = await create_row(
        db_session, owner_id, status=RPSStatus.PROCESSED, source_document=None
    )
    second = await create_row(
        db_session, owner_id, status=RPSStatus.PROCESSED, source_document=None
    )

    report = await reprocess_legacy_rps(
        session_factory=lambda: session_scope(db_session),
        service_factory=lambda _session: FailingService(),
    )

    assert report.selected == 2
    assert report.processed == 0
    assert report.failed == 2
    assert {rps_id for rps_id, _reason in report.errors} == {first, second}
    assert all("tidak dapat dibaca" in reason for _, reason in report.errors)
    assert report.exit_code == 1


@pytest.mark.asyncio
async def test_limit_is_applied_to_the_selection(db_session, owner_id):
    for _ in range(3):
        await create_row(
            db_session, owner_id, status=RPSStatus.PROCESSED, source_document=None
        )

    calls: list[tuple[str, str]] = []
    report = await reprocess_legacy_rps(
        limit=2,
        session_factory=lambda: session_scope(db_session),
        service_factory=lambda _session: RecordingService(calls),
    )

    assert report.selected == 2
    assert report.processed == 2
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_a_non_positive_limit_is_rejected(db_session):
    with pytest.raises(ValueError):
        await reprocess_legacy_rps(
            limit=0, session_factory=lambda: session_scope(db_session)
        )
