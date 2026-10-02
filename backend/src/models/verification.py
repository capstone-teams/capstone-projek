import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class VerificationStatus(str, enum.Enum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class Verification(BaseModel):
    __tablename__ = "verifications"

    course_id: Mapped[str] = mapped_column(
        ForeignKey("course.id"),
        nullable=False,
        index=True,
    )

    execution_id: Mapped[str] = mapped_column(
        ForeignKey("moodle_executions.id"),
        nullable=False,
    )

    # Polymorphic reference (Course / Section / Content / Activity), so
    # intentionally not a single-table foreign key.
    target_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    target_id: Mapped[str] = mapped_column(
        nullable=False,
    )

    status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status"),
        nullable=False,
        default=VerificationStatus.UNKNOWN,
    )

    expected_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    actual_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    discrepancies: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
