"""Representasi domain RPS (BE-05).

``RPSDocument`` adalah domain model, bukan entity persistence: ia hanya memuat
aturan bentuk dan lifecycle dokumen RPS, tanpa mengetahui tabel, session, maupun
SQLAlchemy. Entity tabelnya tetap ``src.models.rps.RPS`` (BE-02) yang diakses
melalui :class:`~src.services.rps.repository.RPSRepository`.

Yang sengaja **tidak** ada di sini:

- pemetaan ke tabel ``rps_analyses`` — itu hasil ekstraksi (BE-08), bukan
  dokumen unggahan;
- isi hasil konversi (JSON, YAML, tabel) — ``source_document`` hanya disimpan
  sebagai atribut; YAML baru dibentuk BE-08.1 saat dibutuhkan (DL-006);
- apa pun dari HTTP layer (request/response/FastAPI).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from src.schemas.rps_structured import RPS_SCHEMA_VERSION
from src.services.rps.enums import RPSStatus
from src.services.rps.errors import RPSStateError, RPSValidationError
from src.services.rps.validation import (
    compute_file_hash,
    file_extension,
    normalize_file_hash,
    normalize_file_name,
    normalize_file_path,
    normalize_file_type,
    normalize_identifier,
    normalize_schema_version,
    normalize_status,
)

__all__ = ["MAX_ERROR_CODE_LENGTH", "RPSDocument", "require_owner"]

# Panjang kolom ``rps.processing_error_code`` (String(50)); kode error pada
# design-api §18 jauh lebih pendek, batas ini hanya menjaga kolomnya.
MAX_ERROR_CODE_LENGTH = 50


@dataclass(kw_only=True, slots=True)
class RPSDocument:
    """Dokumen RPS yang diunggah beserta status pemrosesannya.

    Setiap ``RPSDocument`` yang berhasil dibentuk sudah tervalidasi (nama file
    aman, hash berbentuk SHA-256, status berupa enum kanonik), sehingga invariant
    domain tetap terjaga di seluruh application layer.

    ``file_path`` adalah path **relatif** terhadap root storage; lokasi absolut
    hanya diketahui oleh :mod:`src.services.rps.storage`, sehingga pemindahan
    direktori penyimpanan tidak mengubah nilai yang tersimpan di database.
    """

    owner_id: str
    file_name: str
    file_type: str
    file_path: str
    file_hash: str
    schema_version: str = RPS_SCHEMA_VERSION
    status: RPSStatus = RPSStatus.UPLOADED
    id: str | None = None
    source_document: dict[str, Any] | None = None
    processing_duration_ms: int | None = None
    processing_error_code: str | None = None
    processing_error: str | None = None
    structured_data: dict[str, Any] | None = None
    analyzed_at: datetime | None = None
    workflow_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self.file_name = normalize_file_name(self.file_name)
        self.file_type = normalize_file_type(self.file_type)
        self.file_path = normalize_file_path(self.file_path)
        self.file_hash = normalize_file_hash(self.file_hash)
        self.schema_version = normalize_schema_version(self.schema_version)
        self.status = normalize_status(self.status)
        self.id = normalize_identifier(self.id)
        self.owner_id = require_owner(self.owner_id)
        self.workflow_id = normalize_identifier(self.workflow_id)
        self.analyzed_at = _normalize_analyzed_at(self.analyzed_at)
        self.source_document = _normalize_source_document(self.source_document)
        self.processing_duration_ms = _normalize_duration(self.processing_duration_ms)

    @classmethod
    def register(
        cls,
        *,
        owner_id: str,
        file_name: str,
        file_path: str,
        content: bytes,
        file_hash: str | None = None,
        schema_version: str = RPS_SCHEMA_VERSION,
    ) -> RPSDocument:
        """Membentuk dokumen RPS baru yang belum dipersist.

        ``file_hash`` dihitung dari isi file (bukan dari nama atau waktunya),
        sehingga unggahan ulang dokumen yang sama selalu menghasilkan hash yang
        sama dan dapat dikenali sebagai dokumen yang sudah pernah diproses.
        Pemanggil yang sudah menghitung hash (mis. untuk memeriksa duplikat lebih
        dulu) boleh menyerahkannya lewat ``file_hash`` agar isi file tidak
        di-hash dua kali. Status awal selalu ``UPLOADED``; identifier dan
        timestamp dibiarkan ``None`` karena dibentuk oleh database.
        """
        extension = file_extension(file_name)
        if not extension:
            raise RPSValidationError("file_name", "harus memiliki ekstensi file")

        return cls(
            owner_id=owner_id,
            file_name=file_name,
            file_type=normalize_file_type(extension),
            file_path=file_path,
            file_hash=file_hash if file_hash is not None else compute_file_hash(content),
            schema_version=schema_version,
            status=RPSStatus.UPLOADED,
        )

    @property
    def is_processed(self) -> bool:
        """Apakah dokumen sudah selesai dikonversi."""
        return self.status is RPSStatus.PROCESSED

    @property
    def is_processing(self) -> bool:
        """Apakah dokumen sedang dikonversi."""
        return self.status is RPSStatus.PROCESSING

    @property
    def is_analyzing(self) -> bool:
        """Apakah dokumen sedang dianalisis (BE-08.2)."""
        return self.status is RPSStatus.ANALYZING

    @property
    def is_analyzed(self) -> bool:
        """Apakah analisis dokumen sudah selesai dan hasilnya tersimpan."""
        return self.status is RPSStatus.ANALYZED and self.structured_data is not None

    def belongs_to(self, owner_id: str) -> bool:
        """Apakah dokumen dimiliki user tertentu (dasar scoping akses)."""
        return self.owner_id == owner_id

    def already_processed_as(self, *, file_hash: str, schema_version: str) -> bool:
        """Apakah dokumen ini sudah diproses untuk hash dan versi skema tertentu.

        Inilah kunci idempotency BE-05: dokumen dengan ``file_hash`` **dan**
        ``schema_version`` yang sama tidak diproses ulang. Perubahan versi skema
        membuat hasil lama tidak berlaku lagi, sehingga pemrosesan ulang justru
        diperlukan.

        Hasil harus berupa ``source_document`` (JSON Docling). Baris lama yang
        hanya menyimpan Markdown — format sebelum BE-13 — karenanya **tidak**
        dianggap sudah diproses dan akan dikonversi ulang secara otomatis saat
        ``POST /process`` dipanggil.
        """
        return (
            self.is_processed
            and self.source_document is not None
            and self.file_hash == normalize_file_hash(file_hash)
            and self.schema_version == normalize_schema_version(schema_version)
        )

    def retarget_schema_version(self, schema_version: str) -> None:
        """Ubah versi skema yang berlaku untuk dokumen ini.

        Dipakai ketika dokumen diproses ulang untuk versi skema yang lebih baru:
        hasil lama tidak berlaku lagi, dan dokumen harus mencatat versi yang
        benar-benar dipakai agar kunci idempotency (``file_hash`` +
        ``schema_version``) tetap jujur.
        """
        self.schema_version = normalize_schema_version(schema_version)

    def start_processing(
        self,
        *,
        stale_after: timedelta | None = None,
        now: datetime | None = None,
    ) -> None:
        """Tandai dokumen sedang diproses.

        Mengizinkan ``UPLOADED``/``FAILED``/``PROCESSED`` → ``PROCESSING``
        (yang terakhir untuk pemrosesan ulang setelah versi skema berubah),
        tetapi menolak dokumen yang **sedang** diproses: dua pemrosesan
        bersamaan atas satu dokumen hanya akan saling menimpa hasil.

        ``stale_after`` memberi jalan keluar dari kebuntuan: pemrosesan yang
        berjalan di background dapat berhenti di tengah jalan (proses server
        dimatikan, container dibuat ulang), dan tanpa batas waktu baris
        ``PROCESSING`` akan terkunci selamanya. Bila ``updated_at`` lebih tua
        dari ``stale_after``, dokumen dianggap terlantar dan boleh diambil alih.
        """
        if self.is_processing and not self._is_stale(stale_after=stale_after, now=now):
            raise RPSStateError(f"rps {self.id} sedang diproses")

        self.status = RPSStatus.PROCESSING

    def complete_processing(
        self,
        source_document: dict[str, Any],
        *,
        duration_ms: int | None = None,
    ) -> None:
        """Tandai dokumen selesai diproses beserta hasil konversinya.

        Hanya berlaku dari status ``PROCESSING``: menyimpan hasil konversi pada
        dokumen yang tidak sedang diproses berarti ada langkah lifecycle yang
        terlewat.

        ``source_document`` wajib berisi representasi penuh dokumen hasil
        konversi (DoclingDocument sebagai JSON) — satu-satunya format hasil yang
        diakui (DL-008, BE-13). ``duration_ms`` mencatat durasi konversi supaya
        tahap berikutnya (BE-08) tidak perlu menjalankan Docling ulang dan
        performanya dapat dievaluasi.
        """
        if not self.is_processing:
            raise RPSStateError(
                f"rps {self.id} tidak sedang diproses (status: {self.status.value})"
            )

        document = _normalize_source_document(source_document)
        if document is None:
            raise RPSValidationError(
                "source_document", "wajib diisi dengan JSON hasil konversi"
            )

        self.source_document = document
        self.processing_duration_ms = _normalize_duration(duration_ms)
        # Hasil yang berhasil menggantikan catatan kegagalan sebelumnya.
        self.processing_error_code = None
        self.processing_error = None
        self.status = RPSStatus.PROCESSED

    def fail_processing(self, *, error_code: str | None = None, reason: str | None = None) -> None:
        """Tandai pemrosesan gagal beserta alasan yang dapat dibaca client.

        Dokumen tetap disimpan (file aslinya dipertahankan agar hasil dapat
        dilacak ke sumbernya — data-model §8) dan dapat diproses ulang setelah
        penyebab kegagalan diperbaiki. ``source_document`` tidak diisi: hasil
        yang gagal bukan hasil.

        ``error_code`` dan ``reason`` diisi dari error domain yang menyebabkannya
        (kode pada design-api §18 dan alasan publik yang aman ditampilkan), lalu
        dibaca client lewat polling — konversi berjalan di background, sehingga
        tidak ada response request yang dapat membawa kegagalannya.
        """
        self.status = RPSStatus.FAILED
        self.processing_error_code = _normalize_error_code(error_code)
        self.processing_error = _normalize_error_reason(reason)

    def start_analysis(
        self,
        *,
        workflow_id: str,
        allow_reanalysis: bool = False,
        stale_after: timedelta | None = None,
        now: datetime | None = None,
    ) -> None:
        """Tandai dokumen sedang dianalisis menjadi RPS Structured Data.

        Analisis hanya boleh dijalankan dari ``source_document`` yang sudah
        tersimpan — itulah janji "reanalyze tanpa Docling" (design-api §6.6).
        Dokumen yang sedang dikonversi atau sedang dianalisis ditolak supaya dua
        pekerjaan background tidak saling menimpa hasil (``stale_after`` memberi
        jalan keluar bila pekerjaan sebelumnya benar-benar berhenti).

        RPS yang **sudah** ``ANALYZED`` tidak dianalisis ulang secara implisit;
        hanya jalur reanalyze eksplisit yang mengirim ``allow_reanalysis=True``.
        """
        if self.is_processing:
            raise RPSStateError(f"rps {self.id} sedang diproses")
        if self.source_document is None:
            raise RPSValidationError(
                "source_document", "RPS harus diproses sebelum dianalisis"
            )
        if self.is_analyzing and not self._is_stale(stale_after=stale_after, now=now):
            raise RPSStateError(f"rps {self.id} sedang dianalisis")
        if self.is_analyzed and not allow_reanalysis:
            raise RPSStateError(f"rps {self.id} sudah dianalisis")

        self.workflow_id = normalize_identifier(workflow_id)
        if self.workflow_id is None:
            raise RPSValidationError("workflow_id", "wajib diisi")
        self.status = RPSStatus.ANALYZING
        # Catatan kegagalan tahap sebelumnya tidak berlaku lagi untuk percobaan
        # ini; hasil analisis lama tetap disimpan sampai berhasil digantikan.
        self.processing_error_code = None
        self.processing_error = None

    def complete_analysis(
        self,
        structured_data: dict[str, Any],
        *,
        analyzed_at: datetime | None = None,
    ) -> None:
        """Simpan hasil analisis dan tandai dokumen ``ANALYZED``.

        Hasil wajib berupa RPS Structured Data yang sudah tervalidasi (pemanggil
        di application layer memvalidasinya terhadap
        :class:`~src.schemas.rps_structured.RPSStructuredData`). ``analyzed_at``
        dicatat supaya client tahu kapan data ini dihasilkan (design-api §6.4);
        nilai kosong berarti "sekarang".
        """
        if not self.is_analyzing:
            raise RPSStateError(
                f"rps {self.id} tidak sedang dianalisis (status: {self.status.value})"
            )

        data = _normalize_structured_data(structured_data)
        if data is None:
            raise RPSValidationError(
                "structured_data", "wajib diisi dengan hasil analisis"
            )

        self.structured_data = data
        self.analyzed_at = _normalize_analyzed_at(analyzed_at) or datetime.now(timezone.utc)
        self.processing_error_code = None
        self.processing_error = None
        self.status = RPSStatus.ANALYZED

    def fail_analysis(self, *, error_code: str | None = None, reason: str | None = None) -> None:
        """Tandai analisis gagal beserta alasan yang dapat dibaca client.

        Berlaku sama seperti :meth:`fail_processing`: status menjadi ``FAILED``,
        kode dan alasan publik disimpan pada dokumen karena analisis berjalan di
        background. ``structured_data`` dan ``analyzed_at`` hasil analisis
        sebelumnya **tidak** dihapus agar kegagalan reanalyze tidak membuang
        data baik yang terakhir; status ``FAILED`` yang menandai bahwa hasil itu
        bukan hasil terbaru.
        """
        if not self.is_analyzing:
            raise RPSStateError(
                f"rps {self.id} tidak sedang dianalisis (status: {self.status.value})"
            )

        self.status = RPSStatus.FAILED
        self.processing_error_code = _normalize_error_code(error_code)
        self.processing_error = _normalize_error_reason(reason)

    def _is_stale(self, *, stale_after: timedelta | None, now: datetime | None) -> bool:
        """Apakah pemrosesan yang berjalan sudah melewati batas waktunya."""
        if stale_after is None or self.updated_at is None:
            return False

        reference = now or datetime.now(timezone.utc)
        started = self.updated_at
        if started.tzinfo is None:
            # Timestamp dari driver dapat tiba tanpa zona waktu; dokumen
            # disimpan dalam UTC, jadi nilainya ditafsirkan sebagai UTC.
            started = started.replace(tzinfo=timezone.utc)
        return reference - started > stale_after

    def __repr__(self) -> str:
        # Isi dokumen sumber tidak ikut direpresentasikan: dokumen RPS dapat
        # berisi ribuan baris dan repr-nya dipakai pada log.
        document = "set" if self.source_document else "unset"
        return (
            f"RPSDocument(id={self.id!r}, owner_id={self.owner_id!r}, "
            f"file_name={self.file_name!r}, file_type={self.file_type!r}, "
            f"file_hash={self.file_hash!r}, schema_version={self.schema_version!r}, "
            f"status={self.status.value!r}, source_document={document}, "
            f"processing_duration_ms={self.processing_duration_ms!r}, "
            f"created_at={self.created_at!r}, updated_at={self.updated_at!r})"
        )


def _normalize_error_code(value: object) -> str | None:
    """Kode error pada envelope design-api §18: huruf besar, pendek, tanpa spasi."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise RPSValidationError("processing_error_code", "harus berupa teks atau None")

    code = value.strip().upper()
    if not code:
        return None
    if len(code) > MAX_ERROR_CODE_LENGTH:
        raise RPSValidationError(
            "processing_error_code", f"maksimal {MAX_ERROR_CODE_LENGTH} karakter"
        )
    return code


def _normalize_error_reason(value: object) -> str | None:
    """Alasan publik kegagalan; teks kosong berarti tidak ada alasan."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise RPSValidationError("processing_error", "harus berupa teks atau None")

    reason = value.strip()
    return reason or None


def _normalize_source_document(value: object) -> dict[str, Any] | None:
    """Representasi dokumen hasil konversi harus berupa object JSON."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise RPSValidationError("source_document", "harus berupa object JSON atau None")
    if not value:
        raise RPSValidationError("source_document", "tidak boleh kosong")
    return value


def _normalize_structured_data(value: object) -> dict[str, Any] | None:
    """Hasil analisis harus berupa object JSON berisi RPS Structured Data."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise RPSValidationError(
            "structured_data", "harus berupa object JSON atau None"
        )
    if not value:
        raise RPSValidationError("structured_data", "tidak boleh kosong")
    return value


def _normalize_analyzed_at(value: object) -> datetime | None:
    """Waktu analisis adalah timestamp, bukan teks bebas."""
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise RPSValidationError("analyzed_at", "harus berupa datetime atau None")
    return value


def _normalize_duration(value: object) -> int | None:
    """Durasi konversi dalam milidetik; nol/negatif tidak bermakna."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise RPSValidationError("processing_duration_ms", "harus berupa bilangan bulat")
    if value <= 0:
        raise RPSValidationError("processing_duration_ms", "harus lebih besar dari 0")
    return value


def require_owner(value: object) -> str:
    """Owner wajib ada dan berbentuk ShortUUID (FK ke ``users.id``).

    Dipakai bersama oleh service dan storage supaya aturan "siapa pemilik
    dokumen" hanya didefinisikan sekali.
    """
    identifier = normalize_identifier(value)
    if identifier is None:
        raise RPSValidationError("owner_id", "wajib diisi")
    return identifier
