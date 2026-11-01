"""RPS Service — operasi aplikasi terhadap dokumen RPS (BE-05 & BE-08.2).

Service ini menjawab "operasi apa yang boleh dilakukan terhadap dokumen RPS?",
bukan "bagaimana berkasnya disimpan?" (itu
:mod:`src.services.rps.storage") dan bukan "bagaimana dokumen dikonversi/dianalisis?"
(itu :mod:`src.services.rps.converter` beserta adapter Docling-nya, dan
:mod:`src.services.rps.analyzer` beserta service analisis BE-09.2).

Operasi yang disediakan:

- :meth:`RPSService.upload_rps` — validasi berkas, hitung ``file_hash``, simpan
  berkas asli, lalu catat dokumennya (BE-05.1);
- :meth:`RPSService.begin_processing` — bagian pemrosesan yang dijalankan **saat
  request**: periksa idempotency lalu tandai dokumen ``PROCESSING``;
- :meth:`RPSService.attach_workflow` — tautkan dokumen ke workflow orkestrasi
  (BE-11.2) sebelum pekerjaan background dijadwalkan;
- :meth:`RPSService.convert` — konversi dokumen yang sudah ``PROCESSING``
  (dijalankan di luar siklus request; lihat :mod:`src.services.rps.runner`);
- :meth:`RPSService.process_rps` — jalur lengkap keduanya, dipakai pemanggil
  non-HTTP dan pengujian;
- :meth:`RPSService.begin_analysis` / :meth:`RPSService.analyze` — permulaan dan
  jalannya analisis dari ``source_document`` (BE-08.2, luar siklus request);
- :meth:`RPSService.complete_analysis` / :meth:`RPSService.fail_analysis` —
  pencatatan hasil atau kegagalan analisis;
- :meth:`RPSService.list_rps` / :meth:`RPSService.get_analysis` — operasi baca
  yang dipakai endpoint daftar dan hasil analisis (BE-08.3).

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

**Analisis.** Dokumen yang sudah ``ANALYZED`` tidak dianalisis ulang secara
implisit: :meth:`begin_analysis` mengembalikan ``scheduled=False`` kecuali
pemanggil meminta reanalyze eksplisit (``force=True``), dan hasil model selalu
divalidasi terhadap RPS Structured Data sebelum disimpan.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import shortuuid
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.schemas.rps_structured import RPS_SCHEMA_VERSION, RPSStructuredData
from src.services.rps.analyzer import EmitEvent, RPSAnalyzer, analyze_document
from src.services.rps.converter import (
    DocumentConversion,
    DocumentConverter,
    has_extractable_content,
)
from src.services.rps.domain import RPSDocument, require_owner
from src.services.rps.errors import (
    DocumentConversionError,
    RPSAnalysisFailedError,
    RPSDomainError,
    RPSNotFoundError,
    RPSStateError,
    RPSValidationError,
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
from src.services.rps.yaml_export import document_to_yaml

__all__ = [
    "RPSAnalysisStart",
    "RPSConversionResult",
    "RPSProcessResult",
    "RPSProcessStart",
    "RPSService",
    "RPSUploadResult",
]

# Nama artefak konversi yang ditulis di samping dokumen asli. Hasil konversi
# disimpan sebagai JSON (DL-008); YAML tidak dibentuk di sini karena baru
# diserialisasi BE-08.1 saat dibutuhkan sebagai input LLM (DL-006).
DOCUMENT_JSON_ARTIFACT = "document.json"
TABLES_ARTIFACT = "tables.json"
MANIFEST_ARTIFACT = "conversion.json"


@dataclass(frozen=True, slots=True)
class RPSUploadResult:
    """Hasil unggahan: dokumennya, dan apakah ia sudah ada sebelumnya."""

    document: RPSDocument
    deduplicated: bool


@dataclass(frozen=True, slots=True)
class RPSProcessStart:
    """Hasil tahap permulaan pemrosesan (bagian yang berjalan saat request).

    ``reused=True`` berarti tidak ada pekerjaan yang perlu dijadwalkan: dokumen
    sudah diproses untuk ``file_hash`` dan ``schema_version`` yang sama
    (acceptance criteria BE-05).
    """

    document: RPSDocument
    reused: bool


@dataclass(frozen=True, slots=True)
class RPSAnalysisStart:
    """Hasil tahap permulaan analisis (bagian yang berjalan saat request).

    ``scheduled=False`` berarti tidak ada pekerjaan yang perlu dijadwalkan:
    dokumen sudah ``ANALYZED`` dan pemanggil tidak meminta reanalyze. Nilai itu
    dipakai orkestrator BE-11.2 agar analisis tidak berjalan dua kali untuk
    dokumen yang sama. ``workflow_id`` adalah workflow yang menjalankan analisis
    (atau workflow terakhir bila tidak dijadwalkan).
    """

    document: RPSDocument
    scheduled: bool
    workflow_id: str


@dataclass(frozen=True, slots=True)
class RPSConversionResult:
    """Hasil konversi satu dokumen."""

    document: RPSDocument
    conversion: DocumentConversion


@dataclass(frozen=True, slots=True)
class RPSProcessResult:
    """Hasil pemrosesan lengkap (permulaan + konversi)."""

    document: RPSDocument
    reused: bool
    conversion: DocumentConversion | None = None


class RPSService:
    """Operasi aplikasi terhadap dokumen RPS (unggah, ambil, proses)."""

    def __init__(
        self,
        repository: RPSRepository,
        storage: DocumentStorage,
        converter: DocumentConverter,
        analyzer: RPSAnalyzer | None = None,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._converter = converter
        self._analyzer = analyzer or analyze_document

    @classmethod
    def from_session(
        cls,
        session: AsyncSession,
        *,
        storage: DocumentStorage | None = None,
        converter: DocumentConverter | None = None,
        analyzer: RPSAnalyzer | None = None,
    ) -> RPSService:
        """Bangun service dengan dependency bawaan (storage lokal + Docling).

        ``storage``, ``converter``, dan ``analyzer`` dapat diganti pemanggil —
        dipakai pengujian untuk memakai penyimpanan sementara, konverter
        pengganti, dan analisis palsu tanpa menjalankan model ML maupun model
        bahasa.
        """
        return cls(
            repository=RPSRepository(session),
            storage=storage or get_document_storage(),
            converter=converter or get_document_converter(),
            analyzer=analyzer or analyze_document,
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

    async def begin_processing(
        self,
        *,
        rps_id: str,
        owner_id: str,
        schema_version: str | None = None,
    ) -> RPSProcessStart:
        """Siapkan pemrosesan: periksa idempotency, tandai ``PROCESSING``.

        Inilah bagian yang berjalan **saat request**. Konversinya sendiri
        dijalankan di background (design-api §6.3), sehingga request tidak
        tertahan selama model Docling bekerja.

        Bila dokumen sudah diproses untuk ``file_hash`` + ``schema_version`` yang
        sama, tidak ada yang ditandai dan ``reused=True`` dikembalikan.
        """
        document = await self.get_rps(rps_id=rps_id, owner_id=owner_id)
        target_version = normalize_schema_version(schema_version or document.schema_version)

        if document.already_processed_as(
            file_hash=document.file_hash, schema_version=target_version
        ):
            return RPSProcessStart(document=document, reused=True)

        document.retarget_schema_version(target_version)
        document.start_processing(stale_after=self._processing_lease())
        persisted = await self._persist(document)
        return RPSProcessStart(document=persisted, reused=False)

    async def attach_workflow(
        self, *, rps_id: str, owner_id: str, workflow_id: str
    ) -> RPSDocument:
        """Tautkan dokumen RPS ke workflow yang menjalankan pemrosesannya.

        BE-11.2 membuat workflow saat request ``POST /rps/{id}/process`` dan
        menautkannya sebelum orkestrator dijadwalkan, sehingga ``GET /rps/{id}``
        dan daftar RPS menampilkan ``workflow_id`` sejak awal. Kolom yang sama
        dipakai analisis (BE-08.2), jadi reanalyze tetap menunjuk workflow yang
        sama.
        """
        document = await self.get_rps(rps_id=rps_id, owner_id=owner_id)
        document.link_workflow(workflow_id)
        return await self._persist(document)

    async def convert(self, *, rps_id: str, owner_id: str) -> RPSConversionResult:
        """Konversi dokumen yang sudah berstatus ``PROCESSING``.

        Dipanggil di luar siklus request (lihat
        :func:`src.services.rps.runner.run_rps_processing`), sehingga kegagalan
        apa pun berakhir sebagai status ``FAILED`` pada dokumen — bukan sebagai
        500 yang menggantung di request.
        """
        document = await self.get_rps(rps_id=rps_id, owner_id=owner_id)
        if not document.is_processing:
            raise RPSDomainError(
                f"rps {document.id} tidak sedang diproses (status: {document.status.value})"
            )

        started_at = time.perf_counter()
        try:
            content = await self._storage.read_document(document.file_path)
            conversion = await self._converter.convert(
                content=content, file_name=document.file_name
            )
            _require_usable_document(conversion)
            duration_ms = _elapsed_ms(started_at)
            # Artefak ditulis sebelum status diubah menjadi PROCESSED: dokumen
            # yang tercatat selesai harus benar-benar punya hasilnya.
            await self._write_artifacts(document, conversion, duration_ms=duration_ms)
        except RPSDomainError as exc:
            await self._mark_failed(document, error=exc)
            raise
        except Exception as exc:
            failure = DocumentConversionError(
                f"pemrosesan dokumen gagal: {type(exc).__name__}",
                public_reason="Dokumen RPS gagal diproses karena kesalahan tak terduga.",
            )
            await self._mark_failed(document, error=failure)
            raise failure from exc

        document.complete_processing(
            conversion.document_json,
            duration_ms=duration_ms,
        )
        persisted = await self._persist(document)
        return RPSConversionResult(document=persisted, conversion=conversion)

    async def process_rps(
        self,
        *,
        rps_id: str,
        owner_id: str,
        schema_version: str | None = None,
    ) -> RPSProcessResult:
        """Jalankan pemrosesan lengkap secara langsung (permulaan + konversi).

        Endpoint HTTP memakai :meth:`begin_processing` + background runner agar
        request tidak tertahan; jalur ini disediakan untuk pemanggil non-HTTP
        (skrip, pengujian, dan pekerjaan lanjutan) yang memang ingin menunggu
        hasilnya.
        """
        start = await self.begin_processing(
            rps_id=rps_id, owner_id=owner_id, schema_version=schema_version
        )
        if start.reused:
            return RPSProcessResult(document=start.document, reused=True)

        result = await self.convert(rps_id=rps_id, owner_id=owner_id)
        return RPSProcessResult(
            document=result.document, reused=False, conversion=result.conversion
        )

    async def list_rps(self, *, owner_id: str) -> list[RPSDocument]:
        """Daftar RPS milik dosen yang login (design-api §6.5).

        Scoping owner dilakukan repository, sehingga daftar ini tidak pernah
        memuat dokumen milik dosen lain.
        """
        return await self._repository.list_by_owner(require_owner(owner_id))

    async def get_analysis(self, *, rps_id: str, owner_id: str) -> RPSDocument:
        """Dokumen yang hasil analisisnya sudah tersedia (design-api §6.4).

        RPS yang belum dianalisis menghasilkan 422 ``INVALID_REQUEST`` — lebih
        jelas daripada response kosong yang membuat client menebak apakah data
        memang tidak ada atau analisisnya belum berjalan.
        """
        document = await self.get_rps(rps_id=rps_id, owner_id=owner_id)
        if not document.is_analyzed or document.analyzed_at is None:
            raise RPSValidationError("status", "RPS belum dianalisis")
        return document

    async def begin_analysis(
        self,
        *,
        rps_id: str,
        owner_id: str,
        force: bool = False,
        workflow_id: str | None = None,
    ) -> RPSAnalysisStart:
        """Siapkan analisis: periksa state, tandai ``ANALYZING``, tentukan workflow.

        Inilah bagian yang berjalan **saat request**; analisisnya dijalankan
        background runner (design-api §6.6). Dokumen berstatus ``ANALYZED``
        tidak dianalisis ulang secara implisit: ``force=False`` mengembalikan
        ``scheduled=False`` (dipakai orkestrator BE-11.2), sedangkan endpoint
        reanalyze mengirim ``force=True``.

        ``workflow_id`` boleh diberikan orkestrator (BE-11.2) agar analisis
        tercatat pada workflow yang sama dengan pemrosesan; tanpa itu, dokumen
        mendapat workflow_id sendiri.
        """
        document = await self.get_rps(rps_id=rps_id, owner_id=owner_id)

        if document.is_analyzed and not force:
            if document.workflow_id is None:
                raise RPSStateError(
                    f"rps {document.id} sudah dianalisis tanpa workflow"
                )
            return RPSAnalysisStart(
                document=document,
                scheduled=False,
                workflow_id=document.workflow_id,
            )

        identifier = workflow_id or shortuuid.uuid()
        document.start_analysis(
            workflow_id=identifier,
            allow_reanalysis=force,
            stale_after=self._processing_lease(),
        )
        persisted = await self._persist(document)
        return RPSAnalysisStart(
            document=persisted,
            scheduled=True,
            workflow_id=persisted.workflow_id or identifier,
        )

    async def complete_analysis(
        self,
        *,
        rps_id: str,
        owner_id: str,
        data: RPSStructuredData | dict[str, Any],
        analyzed_at: datetime | None = None,
    ) -> RPSDocument:
        """Simpan hasil analisis tervalidasi dan tandai dokumen ``ANALYZED``.

        Dipanggil background runner di modul ini maupun orkestrator BE-11.2,
        sehingga validasi schema berada di satu tempat: hasil model bahasa tidak
        pernah masuk database tanpa melewati
        :class:`~src.schemas.rps_structured.RPSStructuredData`.
        """
        document = await self.get_rps(rps_id=rps_id, owner_id=owner_id)
        structured = self._validated_structured_data(data)
        document.complete_analysis(
            structured.model_dump(mode="json"), analyzed_at=analyzed_at
        )
        return await self._persist(document)

    async def fail_analysis(
        self,
        *,
        rps_id: str,
        owner_id: str,
        error_code: str | None = None,
        reason: str | None = None,
    ) -> RPSDocument:
        """Tandai analisis gagal beserta alasan publik yang dapat dibaca client."""
        document = await self.get_rps(rps_id=rps_id, owner_id=owner_id)
        document.fail_analysis(error_code=error_code, reason=reason)
        return await self._persist(document)

    async def analyze(
        self,
        *,
        rps_id: str,
        owner_id: str,
        emit_event: EmitEvent | None = None,
    ) -> RPSDocument:
        """Jalankan analisis dokumen ``ANALYZING`` dari ``source_document``.

        Dipanggil di luar siklus request (lihat
        :func:`src.services.rps.analysis_runner.run_rps_analysis` dan orkestrator
        workflow BE-11.2). YAML dibentuk dari JSON Docling yang sudah tersimpan
        (BE-08.1), sehingga Docling tidak dijalankan lagi — acceptance criteria
        "reanalyze tanpa Docling".

        ``emit_event`` diteruskan ke analyzer (BE-09.2) supaya aktivitas agent
        dan retry tercatat sebagai event workflow (BE-11.2). Pemanggil non-HTTP
        yang tidak membutuhkannya boleh mengosongkannya.

        Kegagalan apa pun berakhir sebagai status ``FAILED`` beserta kode dan
        alasan publik pada dokumen, bukan sebagai exception yang menggantung di
        request yang sudah selesai.
        """
        document = await self.get_rps(rps_id=rps_id, owner_id=owner_id)
        if not document.is_analyzing:
            raise RPSStateError(
                f"rps {document.id} tidak sedang dianalisis "
                f"(status: {document.status.value})"
            )

        try:
            if document.source_document is None:
                raise RPSValidationError(
                    "source_document", "RPS harus diproses sebelum dianalisis"
                )
            rps_yaml = document_to_yaml(document.source_document)
            if emit_event is None:
                analyzed = await self._analyzer(rps_yaml)
            else:
                analyzed = await self._analyzer(rps_yaml, emit_event=emit_event)
            structured = self._validated_structured_data(analyzed)
            if not structured.has_academic_content():
                raise RPSAnalysisFailedError(
                    "hasil analisis tidak memuat informasi akademik",
                    public_reason=(
                        "Model tidak menemukan informasi akademik pada dokumen RPS."
                    ),
                )
        except RPSDomainError as exc:
            await self._mark_analysis_failed(document, error=exc)
            raise
        except Exception as exc:
            failure = RPSAnalysisFailedError(
                f"analisis RPS gagal: {type(exc).__name__}",
                public_reason="Analisis RPS gagal karena kesalahan tak terduga.",
            )
            await self._mark_analysis_failed(document, error=failure)
            raise failure from exc

        document.complete_analysis(structured.model_dump(mode="json"))
        return await self._persist(document)

    def _validated_structured_data(
        self, data: RPSStructuredData | dict[str, Any]
    ) -> RPSStructuredData:
        """Validasi hasil analisis terhadap kontrak RPS Structured Data."""
        try:
            return RPSStructuredData.model_validate(data)
        except ValidationError as exc:
            raise RPSValidationError(
                "structured_data", "tidak sesuai schema RPS Structured Data"
            ) from exc

    async def _mark_analysis_failed(
        self, document: RPSDocument, *, error: RPSDomainError
    ) -> None:
        """Catat kegagalan analisis tanpa menutupi error aslinya.

        Kode dan alasan publik error disimpan pada dokumen supaya client yang
        melakukan polling melihat **mengapa** analisis gagal — bukan sekadar
        status ``FAILED``. Detail teknisnya tetap hanya di log server-side.
        Kegagalan pencatatan status tidak boleh menggantikan penyebab sebenarnya.
        """
        try:
            document.fail_analysis(
                error_code=error.error_code, reason=error.public_reason
            )
            await self._persist(document)
        except RPSDomainError:
            pass

    async def _write_artifacts(
        self,
        document: RPSDocument,
        conversion: DocumentConversion,
        *,
        duration_ms: int,
    ) -> None:
        """Tulis artefak konversi (JSON, tabel, manifest) di samping dokumen.

        Tidak ada artefak Markdown maupun YAML: JSON Docling adalah satu-satunya
        hasil konversi (DL-008), sedangkan YAML dibentuk BE-08.1 dari JSON saat
        dibutuhkan (DL-006).
        """
        await self._storage.save_artifacts(
            document_path=document.file_path,
            artifacts={
                DOCUMENT_JSON_ARTIFACT: _to_json_bytes(conversion.document_json),
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
                        "page_count": _page_count(conversion.document_json),
                        "duration_ms": duration_ms,
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

    async def _mark_failed(self, document: RPSDocument, *, error: RPSDomainError) -> None:
        """Catat kegagalan pemrosesan tanpa menutupi error aslinya.

        Kode dan alasan publik error disimpan pada dokumen supaya client yang
        melakukan polling melihat **mengapa** pemrosesan gagal — bukan sekadar
        status ``FAILED``. Detail teknisnya tetap hanya di log server-side.
        """
        document.fail_processing(
            error_code=error.error_code, reason=error.public_reason
        )
        try:
            await self._persist(document)
        except RPSDomainError:
            # Kegagalan pencatatan status tidak boleh menggantikan penyebab
            # sebenarnya; dokumen tetap dapat diproses ulang.
            pass

    def _allowed(self) -> tuple[str, ...]:
        return get_settings().rps_allowed_extensions

    def _processing_lease(self) -> timedelta:
        """Batas waktu pemrosesan yang dianggap masih berjalan (lihat domain)."""
        return timedelta(seconds=get_settings().rps_processing_lease_seconds)


def _elapsed_ms(started_at: float) -> int:
    """Durasi sejak ``started_at`` dalam milidetik (minimal 1).

    Dibulatkan ke atas ke 1 ms supaya durasi yang sangat cepat tidak tercatat
    sebagai 0 — kolomnya hanya menerima nilai positif, dan "0 ms" tidak
    membedakan "hampir instan" dari "tidak tercatat".
    """
    return max(1, round((time.perf_counter() - started_at) * 1000))


def _page_count(document_json: dict[str, object]) -> int:
    """Jumlah halaman yang dilaporkan Docling pada JSON hasil konversi."""
    pages = document_json.get("pages")
    if isinstance(pages, (dict, list)):
        return len(pages)
    return 0


def _require_usable_document(conversion: DocumentConversion) -> None:
    """Tolak hasil konversi yang tidak dapat dipakai tahap berikutnya.

    Diperiksa di sini — bukan hanya di adapter — supaya seluruh konverter
    terikat pada janji yang sama: ``source_document`` yang tidak memuat teks
    maupun tabel berarti konversi **gagal**, bukan dokumen yang berhasil tanpa
    isi. Tanpa pemeriksaan ini, JSON kosong akan muncul sebagai error validasi
    (422) yang menyesatkan, padahal masalahnya ada pada hasil konversi.
    """
    if not has_extractable_content(conversion.document_json):
        raise DocumentConversionError(
            "konversi tidak menghasilkan teks/tabel; dokumen tidak memuat teks yang "
            "dapat diekstrak (aktifkan RPS_CONVERTER_OCR untuk dokumen pindai)",
            public_reason=(
                "Dokumen RPS tidak memuat teks yang dapat diekstrak. Bila RPS berupa "
                "hasil pindai, OCR perlu diaktifkan (RPS_CONVERTER_OCR)."
            ),
        )


def _to_json_bytes(payload: object) -> bytes:
    """Serialisasi artefak JSON: UTF-8, tidak meng-escape karakter non-ASCII."""
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
