"""Representasi domain RPS (BE-05).

``RPSDocument`` adalah domain model, bukan entity persistence: ia hanya memuat
aturan bentuk dan lifecycle dokumen RPS, tanpa mengetahui tabel, session, maupun
SQLAlchemy. Entity tabelnya tetap ``src.models.rps.RPS`` (BE-02) yang diakses
melalui :class:`~src.services.rps.repository.RPSRepository`.

Yang sengaja **tidak** ada di sini:

- pemetaan ke tabel ``rps_analyses`` — itu hasil ekstraksi (BE-08), bukan
  dokumen unggahan;
- isi hasil konversi (markdown, JSON, YAML, tabel) — ``source_markdown`` hanya
  disimpan sebagai atribut, sedangkan artefak besar berada di storage;
- apa pun dari HTTP layer (request/response/FastAPI).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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

__all__ = ["RPSDocument", "require_owner"]


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
    source_markdown: str | None = None
    structured_data: dict[str, Any] | None = None
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

    def belongs_to(self, owner_id: str) -> bool:
        """Apakah dokumen dimiliki user tertentu (dasar scoping akses)."""
        return self.owner_id == owner_id

    def already_processed_as(self, *, file_hash: str, schema_version: str) -> bool:
        """Apakah dokumen ini sudah diproses untuk hash dan versi skema tertentu.

        Inilah kunci idempotency BE-05: dokumen dengan ``file_hash`` **dan**
        ``schema_version`` yang sama tidak diproses ulang. Perubahan versi skema
        membuat hasil lama tidak berlaku lagi, sehingga pemrosesan ulang justru
        diperlukan.
        """
        return (
            self.is_processed
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

    def start_processing(self) -> None:
        """Tandai dokumen sedang diproses.

        Mengizinkan ``UPLOADED``/``FAILED``/``PROCESSED`` → ``PROCESSING``
        (yang terakhir untuk pemrosesan ulang setelah versi skema berubah),
        tetapi menolak dokumen yang **sedang** diproses: dua pemrosesan
        bersamaan atas satu dokumen hanya akan saling menimpa hasil.
        """
        if self.is_processing:
            raise RPSStateError(f"rps {self.id} sedang diproses")

        self.status = RPSStatus.PROCESSING

    def complete_processing(self, source_markdown: str) -> None:
        """Tandai dokumen selesai diproses beserta markdown hasil konversinya.

        Hanya berlaku dari status ``PROCESSING``: menyimpan hasil konversi pada
        dokumen yang tidak sedang diproses berarti ada langkah lifecycle yang
        terlewat.
        """
        if not self.is_processing:
            raise RPSStateError(
                f"rps {self.id} tidak sedang diproses (status: {self.status.value})"
            )
        if not isinstance(source_markdown, str) or not source_markdown.strip():
            raise RPSValidationError(
                "source_markdown", "hasil konversi tidak boleh kosong"
            )

        self.source_markdown = source_markdown
        self.status = RPSStatus.PROCESSED

    def fail_processing(self) -> None:
        """Tandai pemrosesan gagal.

        Dokumen tetap disimpan (file aslinya dipertahankan agar hasil dapat
        dilacak ke sumbernya — data-model §8) dan dapat diproses ulang setelah
        penyebab kegagalan diperbaiki.
        """
        self.status = RPSStatus.FAILED

    def __repr__(self) -> str:
        # Isi markdown tidak ikut direpresentasikan: dokumen RPS dapat berisi
        # ribuan baris dan repr-nya dipakai pada log.
        markdown = "set" if self.source_markdown else "unset"
        return (
            f"RPSDocument(id={self.id!r}, owner_id={self.owner_id!r}, "
            f"file_name={self.file_name!r}, file_type={self.file_type!r}, "
            f"file_hash={self.file_hash!r}, schema_version={self.schema_version!r}, "
            f"status={self.status.value!r}, source_markdown={markdown}, "
            f"created_at={self.created_at!r}, updated_at={self.updated_at!r})"
        )


def require_owner(value: object) -> str:
    """Owner wajib ada dan berbentuk ShortUUID (FK ke ``users.id``).

    Dipakai bersama oleh service dan storage supaya aturan "siapa pemilik
    dokumen" hanya didefinisikan sekali.
    """
    identifier = normalize_identifier(value)
    if identifier is None:
        raise RPSValidationError("owner_id", "wajib diisi")
    return identifier
