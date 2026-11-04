import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import ID_LENGTH, BaseModel

# Panjang kolom versi skema. Nilainya harus menampung versi pada
# ``src.schemas.rps_structured.RPS_SCHEMA_VERSION``; layer ``models/`` tidak
# boleh mengimpor ``schemas/`` (lihat backend/README.md), sehingga batas ini
# dinyatakan sebagai konstanta lokal dan dijaga oleh pengujian.
SCHEMA_VERSION_LENGTH = 50

# Nilai bawaan di sisi database, dipakai sebagai backstop bagi baris yang
# ditulis tanpa melalui domain. Domain selalu mengirim versi yang berlaku
# (``RPSDocument.schema_version``), jadi nilai ini hanya jaring pengaman dan
# harus ikut naik ketika versi skema naik.
DEFAULT_SCHEMA_VERSION = "2.0"


class RPSStatus(str, enum.Enum):
    """Status dokumen RPS — sumber tunggal nilai status (design-api §6.5).

    Urutan normal: ``UPLOADED`` → ``PROCESSING`` → ``PROCESSED`` →
    ``ANALYZING`` → ``ANALYZED``. ``FAILED`` dapat terjadi pada tahap konversi
    maupun analisis; tahap yang gagal dijelaskan oleh ``processing_error_code``.
    """

    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    ANALYZING = "ANALYZING"
    ANALYZED = "ANALYZED"
    FAILED = "FAILED"


class RPS(BaseModel):
    __tablename__ = "rps"

    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    file_path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )

    file_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # Versi RPS Structured Data Schema yang berlaku untuk dokumen ini. Bersama
    # ``file_hash`` ia menjadi kunci idempotency pemrosesan (BE-05): dokumen
    # dengan hash **dan** versi skema yang sama tidak diproses ulang. Karena itu
    # kolomnya NOT NULL — versi yang kosong akan membuat kunci tersebut ambigu.
    schema_version: Mapped[str] = mapped_column(
        String(SCHEMA_VERSION_LENGTH),
        nullable=False,
        server_default=DEFAULT_SCHEMA_VERSION,
    )

    status: Mapped[RPSStatus] = mapped_column(
        Enum(RPSStatus, name="rps_status"),
        nullable=False,
        default=RPSStatus.UPLOADED,
        index=True,
    )

    # Representasi penuh dokumen hasil konversi Docling (DoclingDocument sebagai
    # JSON), termasuk teks, heading, tabel, dan nomor halaman — satu-satunya
    # format hasil konversi (DL-008, BE-13). Disimpan di sini supaya tahap
    # berikutnya (pemetaan field pada BE-08) tidak perlu menjalankan Docling
    # ulang; YAML dibentuk dari kolom ini saat dibutuhkan (DL-006).
    source_document: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Durasi konversi dalam milidetik, dicatat untuk evaluasi performa.
    # NULL berarti dokumen belum pernah selesai diproses.
    processing_duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Kegagalan tahap background (konversi BE-05.2 atau analisis BE-08.2).
    # Karena tahap itu berjalan di background, kegagalan tidak dapat muncul pada
    # response request — client membacanya lewat polling ``GET /rps/{id}``
    # ketika statusnya FAILED. Nilainya sengaja hanya berisi kode error
    # (design-api §18) dan alasan publik yang aman ditampilkan; penyebab
    # teknisnya tetap hanya ada di log server-side. Kedua tahap memakai kolom
    # yang sama karena status ``FAILED`` juga tunggal — kolom terpisah hanya
    # akan membuat client menebak kolom mana yang harus dibaca.
    processing_error_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    processing_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # RPS Structured Data hasil analisis (DL-009). Bentuknya mengikuti
    # ``src.schemas.rps_structured.RPSStructuredData`` — schema yang sama dengan
    # kontrak endpoint analisis, sehingga database dan client tidak menyimpang.
    structured_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Waktu analisis terakhir yang berhasil menghasilkan ``structured_data``.
    # NULL berarti dokumen belum pernah selesai dianalisis. Dipakai response
    # ``GET /rps/{id}/analysis`` (design-api §6.4).
    analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Workflow yang menjalankan analisis dokumen ini (design-api §6.5/§6.6).
    # BE-08.2 mengisinya saat analisis dijadwalkan; BE-11.2 memakai kolom yang
    # sama untuk workflow orkestrasi pemrosesan + analisis, sehingga endpoint
    # daftar/detail cukup membaca satu tempat.
    workflow_id: Mapped[str | None] = mapped_column(
        String(ID_LENGTH),
        nullable=True,
        index=True,
    )
