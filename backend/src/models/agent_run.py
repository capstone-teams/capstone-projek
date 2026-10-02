import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class AgentRunType(str, enum.Enum):
    ANALYSIS = "ANALYSIS"
    PLANNING = "PLANNING"
    GENERATION = "GENERATION"
    VALIDATION = "VALIDATION"
    EXECUTION = "EXECUTION"
    VERIFICATION = "VERIFICATION"


class AgentRunStatus(str, enum.Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    RETRYING = "RETRYING"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class AgentRun(BaseModel):
    __tablename__ = "agent_runs"

    course_id: Mapped[str] = mapped_column(
        ForeignKey("course.id"),
        nullable=False,
        index=True,
    )

    run_type: Mapped[AgentRunType] = mapped_column(
        Enum(AgentRunType, name="agent_run_type"),
        nullable=False,
    )

    status: Mapped[AgentRunStatus] = mapped_column(
        Enum(AgentRunStatus, name="agent_run_status"),
        nullable=False,
        default=AgentRunStatus.CREATED,
        index=True,
    )

    current_stage: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    model_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    model_runtime: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    input_context: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    output_reference: Mapped[dict | None] = mapped_column(
        JSONB,
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
