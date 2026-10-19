"""Test operasi aplikasi RPS (BE-05.1 & BE-05.2).

Service diuji tanpa database dan tanpa Docling:

- repository diganti versi in-memory yang meniru perilaku tabel ``rps``;
- konverter diganti konverter palsu yang mencatat setiap pemanggilan, sehingga
  janji idempotency ("tidak diproses ulang") dapat dibuktikan secara langsung —
  bukan disimpulkan dari status;
- penyimpanan memakai adapter filesystem sungguhan pada ``tmp_path``, karena
  artefak konversi memang harus benar-benar ditulis.

Integrasi dengan PostgreSQL dan Docling sungguhan diuji terpisah pada
``tests/test_rps_postgres.py`` dan ``tests/test_rps_docling_converter.py``.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
import shortuuid

from src.config.settings import get_settings
from src.schemas.rps_structured import RPS_SCHEMA_VERSION
from src.services.rps.converter import (
    ConvertedTable,
    DocumentConversion,
    DocumentConverter,
)
from src.services.rps.domain import RPSDocument
from src.services.rps.enums import RPSStatus
from src.services.rps.errors import (
    DocumentConversionError,
    DocumentStorageError,
    InvalidFileError,
    RPSDomainError,
    RPSNotFoundError,
    RPSStateError,
    RPSValidationError,
)
from src.services.rps.service import (
    DOCUMENT_JSON_ARTIFACT,
    MANIFEST_ARTIFACT,
    TABLES_ARTIFACT,
    RPSService,
)
from src.services.rps.storage import LocalDocumentStorage
from src.services.rps.validation import compute_file_hash

PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
OTHER_PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n%%EOF\n"
INSTRUCTOR_ID = shortuuid.uuid()
OTHER_INSTRUCTOR_ID = shortuuid.uuid()
def database_now() -> datetime:
    """Waktu untuk repository in-memory, meniru ``server_default now()``.

    Memakai waktu berjalan (bukan konstanta) karena ``updated_at`` dipakai domain
    untuk menilai apakah sebuah pemrosesan masih berjalan atau sudah terlantar.
    """
    return datetime.now(timezone.utc)

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


class InMemoryRPSRepository:
    """Repository in-memory dengan semantik query yang sama seperti versi SQL."""

    def __init__(self) -> None:
        self.rows: dict[str, RPSDocument] = {}
        self.created: list[RPSDocument] = []

    async def create(self, document: RPSDocument) -> RPSDocument:
        created_at = database_now()
        persisted = replace(
            document, id=shortuuid.uuid(), created_at=created_at, updated_at=created_at
        )
        self.rows[persisted.id or ""] = persisted
        self.created.append(persisted)
        return persisted

    async def get_by_id(self, rps_id: str) -> RPSDocument | None:
        return self.rows.get(rps_id)

    async def find_by_id_and_owner(self, rps_id: str, owner_id: str) -> RPSDocument | None:
        row = self.rows.get(rps_id)
        if row is None or row.owner_id != owner_id:
            return None
        return row

    async def find_by_hash(
        self,
        *,
        owner_id: str,
        file_hash: str,
        schema_version: str,
        status: RPSStatus | None = None,
    ) -> RPSDocument | None:
        matches = [
            row
            for row in self.rows.values()
            if row.owner_id == owner_id
            and row.file_hash == file_hash
            and row.schema_version == schema_version
            and (status is None or row.status is status)
        ]
        if not matches:
            return None
        return max(matches, key=lambda row: row.created_at or database_now())

    async def update(self, document: RPSDocument) -> RPSDocument | None:
        if document.id is None:
            raise ValueError("update memerlukan dokumen yang sudah dipersist")
        if document.id not in self.rows:
            return None
        persisted = replace(document, updated_at=database_now())
        self.rows[document.id] = persisted
        return persisted


class RecordingConverter(DocumentConverter):
    """Konverter palsu yang mencatat pemanggilan dan dapat disuruh gagal."""

    name = "recording"

    def __init__(
        self, *, document_json: dict | None = None, error: Exception | None = None
    ) -> None:
        self.document_json = SOURCE_DOCUMENT if document_json is None else document_json
        self._error = error
        self.calls: list[dict] = []

    @property
    def version(self) -> str:
        return "test-1"

    async def convert(self, *, content: bytes, file_name: str) -> DocumentConversion:
        self.calls.append({"content": content, "file_name": file_name})
        if self._error is not None:
            raise self._error
        return DocumentConversion(
            document_json=self.document_json,
            tables=[
                ConvertedTable(
                    index=0,
                    page=2,
                    caption="Distribusi Mingguan",
                    html="<table><tr><td>1</td></tr></table>",
                    cells=[["Minggu", "Topik"], ["1", "Basis data"]],
                )
            ],
            converter_name=self.name,
            converter_version=self.version,
        )


@pytest.fixture
def repository() -> InMemoryRPSRepository:
    return InMemoryRPSRepository()


@pytest.fixture
def storage(tmp_path) -> LocalDocumentStorage:
    return LocalDocumentStorage(tmp_path)


@pytest.fixture
def converter() -> RecordingConverter:
    return RecordingConverter()


@pytest.fixture
def service(repository, storage, converter) -> RPSService:
    return RPSService(repository=repository, storage=storage, converter=converter)


async def upload(service: RPSService, **overrides):
    payload = {
        "owner_id": INSTRUCTOR_ID,
        "file_name": "rps-basis-data.pdf",
        "content": PDF_BYTES,
    }
    payload.update(overrides)
    return await service.upload_rps(**payload)


async def upload_and_process(service: RPSService, **overrides):
    result = await upload(service, **overrides)
    processed = await service.process_rps(
        rps_id=result.document.id or "", owner_id=result.document.owner_id
    )
    return result, processed


# --- BE-05.1: unggah dan penyimpanan ---------------------------------------


@pytest.mark.asyncio
async def test_upload_stores_the_file_and_records_the_document(service, repository, storage):
    result = await upload(service)

    document = result.document
    assert not result.deduplicated
    assert document.status is RPSStatus.UPLOADED
    assert document.file_name == "rps-basis-data.pdf"
    assert document.file_type == "PDF"
    assert document.schema_version == RPS_SCHEMA_VERSION
    assert document.id is not None
    assert len(repository.rows) == 1
    assert await storage.read_document(document.file_path) == PDF_BYTES


@pytest.mark.asyncio
async def test_upload_records_the_hash_of_the_content(service):
    result = await upload(service)

    assert result.document.file_hash == compute_file_hash(PDF_BYTES)


@pytest.mark.asyncio
async def test_upload_stores_the_file_under_a_path_derived_from_its_hash(service):
    result = await upload(service)

    document = result.document
    assert document.file_path == (
        f"{INSTRUCTOR_ID}/{document.file_hash[:2]}/{document.file_hash}.pdf"
    )
    # Nama dari client tidak pernah menjadi bagian dari path penyimpanan.
    assert "rps-basis-data" not in document.file_path


@pytest.mark.asyncio
async def test_upload_rejects_an_unsupported_extension(service, repository, storage, tmp_path):
    with pytest.raises(InvalidFileError):
        await upload(service, file_name="rps.docx", content=b"PK\x03\x04docx")

    assert repository.rows == {}
    assert list(tmp_path.rglob("*")) == []


@pytest.mark.asyncio
async def test_upload_rejects_content_that_is_not_really_a_pdf(service):
    with pytest.raises(InvalidFileError):
        await upload(service, content=b"<html>bukan pdf</html>")


@pytest.mark.asyncio
async def test_upload_rejects_a_file_larger_than_the_configured_limit(
    service, repository, monkeypatch
):
    monkeypatch.setattr(get_settings(), "RPS_MAX_UPLOAD_BYTES", 64)

    with pytest.raises(InvalidFileError):
        await upload(service, content=PDF_BYTES + b"x" * 64)

    assert repository.rows == {}


@pytest.mark.asyncio
async def test_a_file_exactly_at_the_limit_is_accepted(service, monkeypatch):
    monkeypatch.setattr(get_settings(), "RPS_MAX_UPLOAD_BYTES", len(PDF_BYTES))

    result = await upload(service)

    assert result.document.status is RPSStatus.UPLOADED


@pytest.mark.asyncio
async def test_upload_follows_the_configured_allowed_extensions(service, monkeypatch):
    """DOCX dapat diaktifkan lewat konfigurasi, tanpa mengubah kode (design-api §6.1)."""
    docx = b"PK\x03\x04" + b"konten docx"
    monkeypatch.setattr(get_settings(), "RPS_ALLOWED_EXTENSIONS", "pdf,docx")

    result = await upload(service, file_name="rps.docx", content=docx)

    assert result.document.file_type == "DOCX"


@pytest.mark.asyncio
async def test_reuploading_the_same_document_does_not_create_a_second_record(
    service, repository, storage, tmp_path
):
    """Acceptance criteria: dokumen dengan hash dan versi skema sama tidak diproses ulang."""
    first = await upload(service)
    second = await upload(service, file_name="salinan-rps.pdf")

    assert second.deduplicated
    assert second.document.id == first.document.id
    assert len(repository.rows) == 1
    assert len([path for path in tmp_path.rglob("*") if path.is_file()]) == 1


@pytest.mark.asyncio
async def test_the_same_document_under_a_new_schema_version_is_a_new_record(
    service, repository
):
    """Versi skema bagian dari kunci idempotency, bukan sekadar metadata."""
    first = await upload(service)
    second = await upload(service, schema_version=OTHER_SCHEMA_VERSION)

    assert not second.deduplicated
    assert second.document.id != first.document.id
    assert second.document.schema_version == OTHER_SCHEMA_VERSION
    assert len(repository.rows) == 2


@pytest.mark.asyncio
async def test_different_documents_are_separate_records(service, repository):
    first = await upload(service)
    second = await upload(service, content=OTHER_PDF)

    assert not second.deduplicated
    assert second.document.file_hash != first.document.file_hash
    assert len(repository.rows) == 2


@pytest.mark.asyncio
async def test_two_instructors_can_upload_the_same_document(service, repository):
    first = await upload(service)
    second = await upload(service, owner_id=OTHER_INSTRUCTOR_ID)

    assert not second.deduplicated
    assert second.document.id != first.document.id
    assert len(repository.rows) == 2


@pytest.mark.asyncio
async def test_get_returns_the_document_of_its_owner(service):
    created = await upload(service)

    found = await service.get_rps(
        rps_id=created.document.id or "", owner_id=INSTRUCTOR_ID
    )

    assert found.id == created.document.id


@pytest.mark.asyncio
async def test_another_instructors_document_is_reported_as_missing(service):
    created = await upload(service)

    with pytest.raises(RPSNotFoundError):
        await service.get_rps(rps_id=created.document.id or "", owner_id=OTHER_INSTRUCTOR_ID)


@pytest.mark.asyncio
@pytest.mark.parametrize("rps_id", ["bukan-id", "3f2504e0-4f89-41d3-9a0c-0305e82c3301"])
async def test_a_malformed_identifier_is_a_validation_error_not_a_lookup(service, rps_id):
    """Identifier cacat adalah input tidak valid (422), bukan "tidak ditemukan"."""
    with pytest.raises(RPSValidationError):
        await service.get_rps(rps_id=rps_id, owner_id=INSTRUCTOR_ID)


@pytest.mark.asyncio
async def test_an_unknown_identifier_is_not_found(service):
    with pytest.raises(RPSNotFoundError):
        await service.get_rps(rps_id=shortuuid.uuid(), owner_id=INSTRUCTOR_ID)


# --- BE-05.2/BE-13: konversi menjadi source_document -----------------------


@pytest.mark.asyncio
async def test_process_converts_the_document_and_stores_the_json(service, converter):
    created = await upload(service)

    result = await service.process_rps(
        rps_id=created.document.id or "", owner_id=INSTRUCTOR_ID
    )

    assert not result.reused
    assert result.document.status is RPSStatus.PROCESSED
    assert result.document.source_document == SOURCE_DOCUMENT
    assert converter.calls == [{"content": PDF_BYTES, "file_name": "rps-basis-data.pdf"}]


@pytest.mark.asyncio
async def test_process_writes_json_and_table_artifacts(service, storage, tmp_path):
    created = await upload(service)

    await service.process_rps(rps_id=created.document.id or "", owner_id=INSTRUCTOR_ID)

    document = await service.get_rps(
        rps_id=created.document.id or "", owner_id=INSTRUCTOR_ID
    )
    artifact_dir = _artifact_dir(tmp_path, document.file_path)

    assert sorted(path.name for path in artifact_dir.iterdir()) == sorted(
        [DOCUMENT_JSON_ARTIFACT, MANIFEST_ARTIFACT, TABLES_ARTIFACT]
    )

    tables = json.loads((artifact_dir / TABLES_ARTIFACT).read_text(encoding="utf-8"))
    assert tables[0]["num_rows"] == 2
    assert tables[0]["num_cols"] == 2
    assert tables[0]["cells"][1] == ["1", "Basis data"]
    assert tables[0]["caption"] == "Distribusi Mingguan"
    assert tables[0]["html"].startswith("<table>")

    document_json = json.loads(
        (artifact_dir / DOCUMENT_JSON_ARTIFACT).read_text(encoding="utf-8")
    )
    assert document_json["schema_name"] == "DoclingDocument"

    manifest = json.loads((artifact_dir / MANIFEST_ARTIFACT).read_text(encoding="utf-8"))
    assert manifest["converter"] == "recording"
    assert manifest["converter_version"] == "test-1"
    assert manifest["table_count"] == 1
    assert manifest["page_count"] == 2
    assert manifest["file_hash"] == document.file_hash
    assert manifest["schema_version"] == RPS_SCHEMA_VERSION
    assert manifest["converted_at"]


@pytest.mark.asyncio
async def test_processing_twice_does_not_run_the_converter_again(service, converter):
    created = await upload(service)
    rps_id = created.document.id or ""

    first = await service.process_rps(rps_id=rps_id, owner_id=INSTRUCTOR_ID)
    second = await service.process_rps(rps_id=rps_id, owner_id=INSTRUCTOR_ID)

    assert not first.reused
    assert second.reused
    assert second.document.status is RPSStatus.PROCESSED
    assert second.document.source_document == SOURCE_DOCUMENT
    assert len(converter.calls) == 1


@pytest.mark.asyncio
async def test_reusing_a_result_requires_both_hash_and_schema_version(service, converter):
    """Meminta versi skema lain berarti memproses ulang, bukan memakai hasil lama."""
    created = await upload(service)
    rps_id = created.document.id or ""

    await service.process_rps(rps_id=rps_id, owner_id=INSTRUCTOR_ID)
    reused = await service.process_rps(
        rps_id=rps_id, owner_id=INSTRUCTOR_ID, schema_version=RPS_SCHEMA_VERSION
    )
    reprocessed = await service.process_rps(
        rps_id=rps_id, owner_id=INSTRUCTOR_ID, schema_version=OTHER_SCHEMA_VERSION
    )

    assert reused.reused
    assert not reprocessed.reused
    assert reprocessed.document.schema_version == OTHER_SCHEMA_VERSION
    assert len(converter.calls) == 2


@pytest.mark.asyncio
async def test_a_failed_conversion_leaves_the_document_failed(service, repository):
    created = await upload(service)
    service._converter = RecordingConverter(
        error=DocumentConversionError("dokumen rusak")
    )

    with pytest.raises(DocumentConversionError) as excinfo:
        await service.process_rps(
            rps_id=created.document.id or "", owner_id=INSTRUCTOR_ID
        )

    document = repository.rows[created.document.id or ""]
    assert document.status is RPSStatus.FAILED
    assert document.source_document is None
    # Pesan publik tidak membocorkan detail penyebab; detailnya hanya di log.
    assert excinfo.value.public_message == "Pemrosesan RPS gagal."
    assert "dokumen rusak" in excinfo.value.log_message


@pytest.mark.asyncio
async def test_a_failed_document_can_be_processed_again(service, repository):
    created = await upload(service)
    rps_id = created.document.id or ""
    service._converter = RecordingConverter(error=DocumentConversionError("gagal"))

    with pytest.raises(DocumentConversionError):
        await service.process_rps(rps_id=rps_id, owner_id=INSTRUCTOR_ID)

    service._converter = RecordingConverter()
    result = await service.process_rps(rps_id=rps_id, owner_id=INSTRUCTOR_ID)

    assert result.document.status is RPSStatus.PROCESSED
    assert result.document.source_document == SOURCE_DOCUMENT


@pytest.mark.asyncio
async def test_an_empty_conversion_result_is_a_failure(service, repository):
    """JSON tanpa teks/tabel bukan hasil yang sah untuk tahap berikutnya."""
    created = await upload(service)
    service._converter = RecordingConverter(
        document_json={"schema_name": "DoclingDocument", "texts": [], "tables": []}
    )

    with pytest.raises(DocumentConversionError):
        await service.process_rps(
            rps_id=created.document.id or "", owner_id=INSTRUCTOR_ID
        )

    assert repository.rows[created.document.id or ""].status is RPSStatus.FAILED


@pytest.mark.asyncio
async def test_a_document_whose_file_disappeared_fails_with_a_storage_error(
    service, repository, storage
):
    created = await upload(service)
    await _delete_document(storage, created.document.file_path)

    with pytest.raises(DocumentStorageError):
        await service.process_rps(
            rps_id=created.document.id or "", owner_id=INSTRUCTOR_ID
        )

    assert repository.rows[created.document.id or ""].status is RPSStatus.FAILED


@pytest.mark.asyncio
async def test_another_instructor_cannot_process_the_document(service, converter):
    created = await upload(service)

    with pytest.raises(RPSNotFoundError):
        await service.process_rps(
            rps_id=created.document.id or "", owner_id=OTHER_INSTRUCTOR_ID
        )

    assert converter.calls == []


@pytest.mark.asyncio
async def test_processing_works_for_a_document_uploaded_by_any_owner(service, repository):
    created = await upload(service, owner_id=OTHER_INSTRUCTOR_ID)

    result = await service.process_rps(
        rps_id=created.document.id or "", owner_id=OTHER_INSTRUCTOR_ID
    )

    assert result.document.status is RPSStatus.PROCESSED
    assert repository.rows[created.document.id or ""].owner_id == OTHER_INSTRUCTOR_ID


@pytest.mark.asyncio
async def test_a_processed_document_keeps_its_file_and_metadata(service):
    """Berkas asli dipertahankan agar hasil tetap dapat dilacak ke sumbernya."""
    created = await upload(service)
    original_hash = created.document.file_hash

    result = await service.process_rps(
        rps_id=created.document.id or "", owner_id=INSTRUCTOR_ID
    )

    assert result.document.file_hash == original_hash
    assert result.document.file_name == "rps-basis-data.pdf"
    assert result.document.created_at is not None


# --- Hasil konversi tersimpan & durasi (issue #98) -------------------------


@pytest.mark.asyncio
async def test_the_converted_document_is_persisted_for_the_next_stage(service, repository):
    """BE-08 memetakan field dari JSON Docling tanpa menjalankan Docling ulang."""
    created = await upload(service)

    result = await service.process_rps(
        rps_id=created.document.id or "", owner_id=INSTRUCTOR_ID
    )

    stored = repository.rows[created.document.id or ""]
    assert result.document.source_document == SOURCE_DOCUMENT
    assert stored.source_document == result.document.source_document
    # Teks, tabel, dan nomor halaman tetap ada pada JSON yang disimpan.
    assert stored.source_document["texts"][0]["text"] == "CPMK"
    assert stored.source_document["tables"][0]["prov"][0]["page_no"] == 2
    assert stored.source_document["pages"]["2"]["page_no"] == 2


@pytest.mark.asyncio
async def test_a_legacy_markdown_only_row_is_reprocessed(service, repository, converter):
    """RPS uji format lama (hanya Markdown) diproses ulang menjadi JSON."""
    created = await upload(service)
    rps_id = created.document.id or ""
    await service.process_rps(rps_id=rps_id, owner_id=INSTRUCTOR_ID)

    # Baris lama: sudah PROCESSED tetapi tidak punya JSON hasil konversi.
    repository.rows[rps_id] = replace(repository.rows[rps_id], source_document=None)

    result = await service.process_rps(rps_id=rps_id, owner_id=INSTRUCTOR_ID)

    assert not result.reused
    assert result.document.status is RPSStatus.PROCESSED
    assert result.document.source_document == SOURCE_DOCUMENT
    assert len(converter.calls) == 2


@pytest.mark.asyncio
async def test_the_processing_duration_is_recorded(service, repository):
    created = await upload(service)

    result = await service.process_rps(
        rps_id=created.document.id or "", owner_id=INSTRUCTOR_ID
    )

    assert result.document.processing_duration_ms >= 1
    assert repository.rows[created.document.id or ""].processing_duration_ms >= 1


@pytest.mark.asyncio
async def test_the_duration_is_also_recorded_in_the_conversion_manifest(service, tmp_path):
    """Manifest menyimpan jejak konversi, termasuk performanya."""
    created = await upload(service)

    result = await service.process_rps(
        rps_id=created.document.id or "", owner_id=INSTRUCTOR_ID
    )

    manifest = json.loads(
        (_artifact_dir(tmp_path, result.document.file_path) / MANIFEST_ARTIFACT).read_text(
            encoding="utf-8"
        )
    )
    assert manifest["duration_ms"] == result.document.processing_duration_ms


@pytest.mark.asyncio
async def test_a_conversion_failure_stores_a_readable_reason(service, repository):
    """Kegagalan background harus terbaca client, bukan hanya status FAILED."""
    created = await upload(service)
    service._converter = RecordingConverter(
        error=DocumentConversionError(
            "detail internal: /var/rps/rahasia.pdf rusak",
            public_reason="Dokumen tidak dapat dibaca.",
        )
    )

    with pytest.raises(DocumentConversionError):
        await service.process_rps(rps_id=created.document.id or "", owner_id=INSTRUCTOR_ID)

    stored = repository.rows[created.document.id or ""]
    assert stored.processing_error_code == "RPS_PROCESSING_FAILED"
    assert stored.processing_error == "Dokumen tidak dapat dibaca."
    # Detail internal tidak ikut tersimpan pada dokumen.
    assert "rahasia" not in (stored.processing_error or "")


@pytest.mark.asyncio
async def test_a_retry_clears_the_previous_failure_record(service, repository):
    created = await upload(service)
    rps_id = created.document.id or ""
    service._converter = RecordingConverter(
        error=DocumentConversionError("gagal", public_reason="Gagal sekali.")
    )

    with pytest.raises(DocumentConversionError):
        await service.process_rps(rps_id=rps_id, owner_id=INSTRUCTOR_ID)
    assert repository.rows[rps_id].processing_error_code == "RPS_PROCESSING_FAILED"

    service._converter = RecordingConverter()
    await service.process_rps(rps_id=rps_id, owner_id=INSTRUCTOR_ID)

    assert repository.rows[rps_id].processing_error_code is None
    assert repository.rows[rps_id].processing_error is None


# --- Pemisahan permulaan dan konversi (pemrosesan background) --------------


@pytest.mark.asyncio
async def test_begin_processing_marks_the_document_without_converting(service, converter):
    """Inilah bagian yang berjalan saat request: tidak menyentuh konverter."""
    created = await upload(service)

    start = await service.begin_processing(
        rps_id=created.document.id or "", owner_id=INSTRUCTOR_ID
    )

    assert not start.reused
    assert start.document.status is RPSStatus.PROCESSING
    assert converter.calls == []


@pytest.mark.asyncio
async def test_convert_finishes_a_document_that_is_already_processing(service, storage, converter):
    created = await upload(service)
    rps_id = created.document.id or ""
    await service.begin_processing(rps_id=rps_id, owner_id=INSTRUCTOR_ID)

    result = await service.convert(rps_id=rps_id, owner_id=INSTRUCTOR_ID)

    assert result.document.status is RPSStatus.PROCESSED
    assert len(converter.calls) == 1


@pytest.mark.asyncio
async def test_convert_refuses_a_document_that_is_not_being_processed(service, converter):
    """Konversi hanya melanjutkan pekerjaan yang memang sudah dijadwalkan."""
    created = await upload(service)

    with pytest.raises(RPSDomainError):
        await service.convert(rps_id=created.document.id or "", owner_id=INSTRUCTOR_ID)

    assert converter.calls == []


@pytest.mark.asyncio
async def test_begin_processing_reuses_a_finished_document(service, converter):
    created = await upload(service)
    rps_id = created.document.id or ""
    await service.process_rps(rps_id=rps_id, owner_id=INSTRUCTOR_ID)

    start = await service.begin_processing(rps_id=rps_id, owner_id=INSTRUCTOR_ID)

    assert start.reused
    assert start.document.status is RPSStatus.PROCESSED
    assert len(converter.calls) == 1


@pytest.mark.asyncio
async def test_a_processing_document_cannot_be_started_again(service, repository):
    created = await upload(service)
    rps_id = created.document.id or ""
    await service.begin_processing(rps_id=rps_id, owner_id=INSTRUCTOR_ID)

    with pytest.raises(RPSStateError):
        await service.begin_processing(rps_id=rps_id, owner_id=INSTRUCTOR_ID)


@pytest.mark.asyncio
async def test_a_stale_processing_document_is_taken_over(service, repository, monkeypatch):
    """Konversi yang terputus tidak boleh mengunci dokumen selamanya."""
    created = await upload(service)
    rps_id = created.document.id or ""
    await service.begin_processing(rps_id=rps_id, owner_id=INSTRUCTOR_ID)

    # Barisnya sudah lama tidak tersentuh, lebih tua dari batas lease.
    stale = repository.rows[rps_id]
    repository.rows[rps_id] = replace(
        stale, updated_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    monkeypatch.setattr(get_settings(), "RPS_PROCESSING_LEASE_SECONDS", 900)

    start = await service.begin_processing(rps_id=rps_id, owner_id=INSTRUCTOR_ID)

    assert not start.reused
    assert start.document.status is RPSStatus.PROCESSING


def _artifact_dir(tmp_path, file_path: str):
    """Direktori artefak milik sebuah dokumen pada penyimpanan uji."""
    from src.services.rps.storage import artifact_dir_for

    return tmp_path / artifact_dir_for(file_path)


async def _delete_document(storage: LocalDocumentStorage, relative_path: str) -> None:
    """Hapus berkas dokumen langsung dari disk (mensimulasikan storage yang hilang)."""
    (storage.root / relative_path).unlink()
