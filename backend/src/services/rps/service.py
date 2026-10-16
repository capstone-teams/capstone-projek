"""RPS Service — operasi aplikasi terhadap dokumen RPS (BE-05.1 & BE-05.2).

Service ini menjawab "operasi apa yang boleh dilakukan terhadap dokumen RPS?",
bukan "bagaimana berkasnya disimpan?" (itu
:mod:`src.services.rps.storage`) dan bukan "bagaimana dokumen dikonversi?" (itu
:mod:`src.services.rps.converter` beserta adapter Docling-nya).

Dua operasi yang disediakan:

- :meth:`RPSService.upload_rps` — validasi berkas, hitung ``file_hash``,
  simpan berkas asli, lalu catat dokumennya (BE-05.1);
- :meth:`RPSService.process_rps` — konversi dokumen menjadi ``source_markdown``
  beserta artefak JSON/YAML/tabel (BE-05.2).

**Idempotency.** Sesuai acceptance criteria BE-05, dokumen dengan ``file_hash``
dan ``schema_version`` yang sama tidak diproses ulang:

- unggahan ulang dokumen identik mengembalikan baris yang sudah ada
  (``deduplicated=True``) alih-alih membuat baris kedua;
- pemrosesan dokumen yang sudah ``PROCESSED`` dengan versi skema yang sama
  mengembalikan hasil yang tersimpan (``reused=True``) tanpa menjalankan
  konverter lagi.

Meminta pemrosesan dengan ``schema_version`` **berbeda** justru memproses ulang:
hasil lama tidak berlaku lagi untuk skema baru, dan dokumen mencatat versi yang
benar-benar dipakai.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.schemas.rps_structured import RPS_SCHEMA_VERSION
from src.services.rps.converter import DocumentConversion, DocumentConverter
from src.services.rps.domain import RPSDocument, require_owner
from src.services.rps.errors import (
    DocumentConversionError,
    RPSDomainError,
    RPSNotFoundError,
)
from src.services.rps.factory import get_document_converter, get_document_storage
from src.services.rps.repository import RPSRepository
from src.services.rps.storage import DocumentStorage
from src.services.rps.validation import (
    compute_file_hash,
    ensure_matches_declared_type,
    ensure_size_within_limit,
    ensure_supported_extension,
    file_extension,
    normalize_identifier,
    normalize_schema_version,
)

__all__ = ["RPSProcessResult", "RPSService", "RPSUploadResult"]

# Nama artefak konversi yang ditulis di samping dokumen asli.
DOCUMENT_JSON_ARTIFACT = "document.json"
DOCUMENT_YAML_ARTIFACT = "document.yaml"
TABLES_ARTIFACT = "tables.json"
MANIFEST_ARTIFACT = "conversion.json"


@dataclass(frozen=True, slots=True)
class RPSUploadResult:
    """Hasil unggahan: dokumennya, dan apakah ia sudah ada sebelumnya."""

    document: RPSDocument
    deduplicated: bool


@dataclass(frozen=True, slots=True)
class RPSProcessResult:
    """Hasil pemrosesan: dokumennya, dan apakah konversi benar-benar dijalankan.

    ``reused=True`` berarti dokumen sudah pernah diproses untuk ``file_hash`` dan
    ``schema_version`` yang sama, sehingga konverter tidak dijalankan lagi
    (acceptance criteria BE-05).
    """

    document: RPSDocument
    reused: bool


class RPSService:
    """Operasi aplikasi terhadap dokumen RPS (unggah, ambil, proses)."""

    def __init__(
        self,
        repository: RPSRepository,
        storage: DocumentStorage,
        converter: DocumentConverter,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._converter = converter

    @classmethod
    def from_session(
        cls,
        session: AsyncSession,
        *,
        storage: DocumentStorage | None = None,
        converter: DocumentConverter | None = None,
    ) -> RPSService:
        """Bangun service dengan dependency bawaan (storage lokal + Docling).

        ``storage`` dan ``converter`` dapat diganti pemanggil — dipakai
        pengujian untuk memakai penyimpanan sementara dan konverter pengganti
        tanpa menjalankan model ML.
        """
        return cls(
            repository=RPSRepository(session),
            storage=storage or get_document_storage(),
            converter=converter or get_document_converter(),
        )

    async def upload_rps(
        self,
        *,
        owner_id: str,
        file_name: str,
        content: bytes,
        schema_version: str = RPS_SCHEMA_VERSION,
    ) -> RPSUploadResult:
        """Terima dokumen RPS: validasi, simpan berkasnya, catat dokumennya.

        Urutan pemeriksaan disengaja: tipe dan ukuran diperiksa **sebelum** apa
        pun disimpan, dan isi berkas diperiksa terhadap tipe yang diklaim
        (design-api §23.8). Dengan begitu berkas yang jelas tidak sah tidak
        pernah menyentuh disk maupun database.
        """
        extension = ensure_supported_extension(file_extension(file_name or ""), self._allowed())
        ensure_size_within_limit(len(content), get_settings().rps_max_upload_bytes)
        ensure_matches_declared_type(content, extension)

        owner = require_owner(owner_id)
        version = normalize_schema_version(schema_version)
        file_hash = compute_file_hash(content)

        existing = await self._repository.find_by_hash(
            owner_id=owner,
            file_hash=file_hash,
            schema_version=version,
        )
        if existing is not None:
            # Dokumen identik sudah pernah diunggah untuk versi skema ini.
            # Mengembalikan baris yang ada menjaga janji "tidak diproses ulang":
            # tidak ada baris baru yang perlu dikonversi lagi.
            return RPSUploadResult(document=existing, deduplicated=True)

        stored = await self._storage.save_document(
            owner_id=owner,
            file_hash=file_hash,
            extension=extension,
            content=content,
        )
        document = RPSDocument.register(
            owner_id=owner,
            file_name=file_name,
            file_path=stored.relative_path,
            content=content,
            file_hash=file_hash,
            schema_version=version,
        )
        created = await self._repository.create(document)
        return RPSUploadResult(document=created, deduplicated=False)

    async def get_rps(self, *, rps_id: str, owner_id: str) -> RPSDocument:
        """Ambil dokumen milik owner; :class:`RPSNotFoundError` bila tidak ada.

        Dokumen milik instruktur lain menghasilkan error yang sama seperti
        dokumen yang tidak ada, sehingga keberadaannya tidak dapat dideteksi
        dari perbedaan response.
        """
        owner = require_owner(owner_id)
        identifier = normalize_identifier(rps_id)
        if identifier is None:
            raise RPSNotFoundError(rps_id)

        document = await self._repository.find_by_id_and_owner(identifier, owner)
        if document is None:
            raise RPSNotFoundError(identifier)
        return document

    async def process_rps(
        self,
        *,
        rps_id: str,
        owner_id: str,
        schema_version: str | None = None,
    ) -> RPSProcessResult:
        """Konversi dokumen menjadi ``source_markdown`` beserta artefaknya.

        Pemrosesan bersifat *synchronous* pada tahap S0: hasilnya sudah tersedia
        ketika response dikembalikan, sehingga status akhir (``PROCESSED`` /
        ``FAILED``) dapat langsung dibaca client. Workflow asynchronous beserta
        Agent Run menyusul pada BE-08, yang memiliki ``course_id`` sebagai
        induk Agent Run (tabel ``agent_runs`` mensyaratkannya).
        """
        document = await self.get_rps(rps_id=rps_id, owner_id=owner_id)
        target_version = normalize_schema_version(schema_version or document.schema_version)

        if document.already_processed_as(
            file_hash=document.file_hash, schema_version=target_version
        ):
            return RPSProcessResult(document=document, reused=True)

        document.retarget_schema_version(target_version)
        document.start_processing()
        await self._persist(document)

        try:
            content = await self._storage.read_document(document.file_path)
            conversion = await self._converter.convert(
                content=content, file_name=document.file_name
            )
            _require_usable_markdown(conversion)
            # Artefak ditulis sebelum status diubah menjadi PROCESSED: dokumen
            # yang tercatat selesai harus benar-benar punya hasilnya.
            await self._write_artifacts(document, conversion)
        except RPSDomainError:
            await self._mark_failed(document)
            raise
        except Exception as exc:
            await self._mark_failed(document)
            raise DocumentConversionError(
                f"pemrosesan dokumen gagal: {type(exc).__name__}"
            ) from exc

        document.complete_processing(conversion.markdown)
        persisted = await self._persist(document)
        return RPSProcessResult(document=persisted, reused=False)

    async def _write_artifacts(
        self, document: RPSDocument, conversion: DocumentConversion
    ) -> None:
        """Tulis artefak konversi (JSON, YAML, tabel, manifest) di samping dokumen."""
        await self._storage.save_artifacts(
            document_path=document.file_path,
            artifacts={
                DOCUMENT_JSON_ARTIFACT: _to_json_bytes(conversion.document_json),
                DOCUMENT_YAML_ARTIFACT: conversion.document_yaml.encode("utf-8"),
                TABLES_ARTIFACT: _to_json_bytes(
                    [table.to_dict() for table in conversion.tables]
                ),
                MANIFEST_ARTIFACT: _to_json_bytes(
                    {
                        "file_hash": document.file_hash,
                        "schema_version": document.schema_version,
                        "converter": conversion.converter_name,
                        "converter_version": conversion.converter_version,
                        "table_count": conversion.table_count,
                        "markdown_length": len(conversion.markdown),
                        "converted_at": datetime.now(timezone.utc).isoformat(),
                    }
                ),
            },
        )

    async def _persist(self, document: RPSDocument) -> RPSDocument:
        """Simpan perubahan dokumen; baris yang hilang di tengah jalan tetap not-found."""
        persisted = await self._repository.update(document)
        if persisted is None:
            raise RPSNotFoundError(document.id)
        return persisted

    async def _mark_failed(self, document: RPSDocument) -> None:
        """Catat kegagalan pemrosesan tanpa menutupi error aslinya."""
        document.fail_processing()
        try:
            await self._persist(document)
        except RPSDomainError:
            # Kegagalan pencatatan status tidak boleh menggantikan penyebab
            # sebenarnya; dokumen tetap dapat diproses ulang.
            pass

    def _allowed(self) -> tuple[str, ...]:
        return get_settings().rps_allowed_extensions


def _require_usable_markdown(conversion: DocumentConversion) -> None:
    """Tolak hasil konversi yang tidak dapat dipakai tahap berikutnya.

    Diperiksa di sini — bukan hanya di adapter — supaya seluruh konverter
    terikat pada janji yang sama: ``source_markdown`` yang kosong berarti
    konversi **gagal**, bukan dokumen yang berhasil tanpa isi. Tanpa
    pemeriksaan ini, markdown kosong akan muncul sebagai error validasi (422)
    yang menyesatkan, padahal masalahnya ada pada hasil konversi.
    """
    if not conversion.markdown.strip():
        raise DocumentConversionError(
            "konversi tidak menghasilkan markdown; dokumen tidak memuat teks yang "
            "dapat diekstrak (aktifkan RPS_CONVERTER_OCR untuk dokumen pindai)"
        )


def _to_json_bytes(payload: object) -> bytes:
    """Serialisasi artefak JSON: UTF-8, tidak meng-escape karakter non-ASCII."""
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
