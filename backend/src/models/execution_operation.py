"""Entity ExecutionOperation (BE-16.1, dipakai tahap eksekusi BE-17.1).

Satu baris adalah satu operasi yang harus dilakukan sebuah eksekusi, mis.
menerapkan section minggu ke-3 ke Moodle. Operasi dibuat bersamaan dengan
eksekusi (status ``PENDING``) sehingga frontend dapat memantau kemajuan per
minggu, lalu diperbarui satu per satu saat dijalankan.

``idempotency_key`` unik per eksekusi: menjalankan eksekusi yang sama dua kali
tidak membuat dua operasi untuk minggu yang sama, dan retry hanya mengulang
operasi berstatus ``FAILED``. ``moodle_object_id`` menyimpan ID objek Moodle
hasil operasi (mis. ID section) supaya hasilnya dapat ditelusuri tanpa memanggil
Moodle lagi.
"""

import enum

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class OperationType(str, enum.Enum):
    """Jenis operasi tingkat konten; M03 baru memakai ``SECTION``."""

    SECTION = "SECTION"
    LEARNING_MATERIAL = "LEARNING_MATERIAL"
    LEARNING_RESOURCE = "LEARNING_RESOURCE"
    ASSIGNMENT = "ASSIGNMENT"
    QUIZ = "QUIZ"


class OperationStatus(str, enum.Enum):
    """Status satu operasi."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    #: Tidak ada yang perlu dikerjakan (mis. rencana tidak berubah pada M04).
    SKIPPED = "SKIPPED"


class ExecutionOperation(BaseModel):
    __tablename__ = "execution_operations"
    __table_args__ = (
        UniqueConstraint(
            "execution_id",
            "idempotency_key",
            name="uq_execution_operations_execution_key",
        ),
        CheckConstraint("retry_count >= 0", name="ck_execution_operations_retry_count"),
    )

    execution_id: Mapped[str] = mapped_column(
        ForeignKey("moodle_executions.id"),
        nullable=False,
        index=True,
    )

    #: Minggu course plan yang diterapkan operasi ini; kosong untuk operasi
    #: tingkat course (mis. pembuatan category di luar M03).
    course_plan_week_id: Mapped[str | None] = mapped_column(
        ForeignKey("course_plan_weeks.id"),
        nullable=True,
        index=True,
    )

    #: Konten yang dieksekusi (dipakai cakupan FULL pada M04). Referensi
    #: polimorfik: learning material/resource ada di ``contents``, assignment/quiz
    #: di ``activities`` — jadi sengaja tidak memakai foreign key satu tabel.
    content_id: Mapped[str | None] = mapped_column(
        nullable=True,
    )

    operation_type: Mapped[OperationType] = mapped_column(
        Enum(OperationType, name="execution_operation_type"),
        nullable=False,
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    moodle_object_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[OperationStatus] = mapped_column(
        Enum(OperationStatus, name="execution_operation_status"),
        nullable=False,
        default=OperationStatus.PENDING,
        index=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
