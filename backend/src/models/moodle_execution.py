import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class MoodleExecutionStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    RETRYING = "RETRYING"


class MoodleExecution(BaseModel):
    __tablename__ = "moodle_executions"

    # Nullable karena tidak semua operasi Moodle harus memiliki
    # course yang sudah tersedia, misalnya pembuatan category.
    course_id: Mapped[str | None] = mapped_column(
        ForeignKey("course.id"),
        nullable=True,
        index=True,
    )

    agent_run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id"),
        nullable=False,
    )

    operation: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Menentukan jenis entity yang sedang diproses.
    # Contoh: course, section, content, activity, category.
    target_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # ID entity lokal yang menggunakan ShortUUID.
    target_id: Mapped[str] = mapped_column(
        String(22),
        nullable=False,
    )

    moodle_object_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    status: Mapped[MoodleExecutionStatus] = mapped_column(
        Enum(MoodleExecutionStatus, name="moodle_execution_status"),
        nullable=False,
        default=MoodleExecutionStatus.PENDING,
        index=True,
    )

    request_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    error_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
