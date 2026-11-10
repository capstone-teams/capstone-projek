"""Entity VerificationResult (BE-21.2).

Satu baris ``verification_results`` adalah **satu kali Moodle verification**
terhadap sebuah eksekusi (Proposal §3.3.8, §3.4.8, §3.6 ``verification_result``):
kondisi course di Moodle dibaca ulang, dibandingkan dengan kondisi yang
diharapkan (course plan dan konten ``APPROVED`` yang dieksekusi), diperbaiki
lewat eksekusi ulang terbatas, lalu hasil akhirnya disimpan di sini.

Berbeda dengan tabel ``verifications`` dari skema awal (satu baris per target),
hasil di sini per eksekusi: daftar perbedaan disimpan sebagai JSON terstruktur
pada ``discrepancies`` (sisa setelah perbaikan) dan ``repaired`` (yang sudah
diperbaiki). Status memakai ``VerificationStatus`` yang sama (Content Schema
§35): ``PASS``, ``PARTIAL``, ``FAIL``, ``UNKNOWN``.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel
from src.models.verification import VerificationStatus


class VerificationResult(BaseModel):
    __tablename__ = "verification_results"
    __table_args__ = (
        *BaseModel.__table_args__,
        CheckConstraint(
            "repair_count >= 0", name="ck_verification_results_repair_count"
        ),
        CheckConstraint(
            "repair_rounds >= 0", name="ck_verification_results_repair_rounds"
        ),
    )

    workflow_id: Mapped[str] = mapped_column(
        ForeignKey("workflows.id"),
        nullable=False,
        index=True,
    )

    execution_id: Mapped[str] = mapped_column(
        ForeignKey("moodle_executions.id"),
        nullable=False,
        index=True,
    )

    status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status"),
        nullable=False,
        default=VerificationStatus.UNKNOWN,
    )

    #: Perbedaan yang masih ada setelah perbaikan (daftar objek JSON).
    discrepancies: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    #: Perbedaan yang ditemukan lalu diperbaiki lewat eksekusi ulang.
    repaired: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    #: Jumlah operasi yang dijalankan ulang untuk perbaikan.
    repair_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    #: Jumlah putaran perbaikan (dibatasi ``MOODLE_VERIFICATION_MAX_REPAIRS``).
    repair_rounds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    #: Ringkasan jumlah section dan activity yang diharapkan dan ditemukan.
    summary: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )