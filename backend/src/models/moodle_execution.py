import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
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

    course_id: Mapped[str] = mapped_column(
        ForeignKey("course.id"),
        nullable=False,
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

    # Polymorphic reference (Course / Section / Content / Activity), so
    # intentionally not a single-table foreign key.
    target_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    target_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
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
