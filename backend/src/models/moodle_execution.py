"""Entity MoodleExecution (BE-16.1, dipakai tahap eksekusi BE-17.1).

Satu baris ``moodle_executions`` adalah **satu run eksekusi** struktur/konten
course plan ke Moodle, bukan satu panggilan Moodle. Operasi individual (section
per minggu, konten, aktivitas pada M04) dicatat pada ``execution_operations``
sehingga satu run dapat dilaporkan sebagai ringkasan berhasil/gagal/dilewati.

``workflow_id`` mengikat eksekusi ke workflow pemiliknya (DL-011): scoping akses
dan transisi status selalu lewat workflow. ``course_plan_id`` menyimpan versi
rencana yang dieksekusi supaya hasil read-back dapat dibandingkan dengan rencana
yang benar-benar dipakai, bukan versi terbaru yang mungkin sudah berubah.

``readback`` menyimpan ringkasan hasil pembacaan ulang struktur course dari
Moodle (jumlah section, urutan, dan nama yang cocok) — data non-sensitif yang
aman ditampilkan ke dosen.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class ExecutionScope(str, enum.Enum):
    """Cakupan eksekusi (DL-012)."""

    #: Section mingguan berdasarkan course plan (M03).
    STRUCTURE = "STRUCTURE"
    #: Section mingguan dan seluruh konten yang disetujui (M04).
    FULL = "FULL"


class ExecutionStatus(str, enum.Enum):
    """Status satu run eksekusi."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

class MoodleExecution(BaseModel):
    __tablename__ = "moodle_executions"

    workflow_id: Mapped[str] = mapped_column(
        ForeignKey("workflows.id"),
        nullable=False,
        index=True,
    )

    course_plan_id: Mapped[str] = mapped_column(
        ForeignKey("course_plans.id"),
        nullable=False,
        index=True,
    )

    #: Course Moodle yang menjadi target; disalin dari workflow saat eksekusi
    #: dibuat agar riwayat tidak berubah ketika dosen mengganti target.
    moodle_course_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    scope: Mapped[ExecutionScope] = mapped_column(
        Enum(ExecutionScope, name="execution_scope"),
        nullable=False,
        default=ExecutionScope.STRUCTURE,
    )

    status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus, name="moodle_execution_status"),
        nullable=False,
        default=ExecutionStatus.PENDING,
        index=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    #: Ringkasan read-back: jumlah section, urutan, dan nama yang cocok.
    readback: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
