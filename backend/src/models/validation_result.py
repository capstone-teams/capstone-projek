import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class ValidationTargetType(str, enum.Enum):
    COURSE_PLAN = "COURSE_PLAN"
    CONTENT = "CONTENT"
    ACTIVITY = "ACTIVITY"
    MOODLE_EXECUTION = "MOODLE_EXECUTION"


class ValidationStatus(str, enum.Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class ValidationResult(BaseModel):
    __tablename__ = "validation_results"

    agent_run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id"),
        nullable=False,
        index=True,
    )

    # Polymorphic reference (Course Plan / Content / Activity / Moodle
    # Execution), so intentionally not a single-table foreign key.
    target_type: Mapped[ValidationTargetType] = mapped_column(
        Enum(ValidationTargetType, name="validation_target_type"),
        nullable=False,
    )

    target_id: Mapped[str] = mapped_column(
        nullable=False,
        index=True,
    )

    status: Mapped[ValidationStatus] = mapped_column(
        Enum(ValidationStatus, name="validation_status"),
        nullable=False,
    )

    checks: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    score: Mapped[float | None] = mapped_column(
        Numeric,
        nullable=True,
    )

    errors: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    warnings: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
