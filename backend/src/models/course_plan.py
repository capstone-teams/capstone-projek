import enum

from sqlalchemy import Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class CoursePlanStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class CoursePlan(BaseModel):
    __tablename__ = "course_plans"
    __table_args__ = (
        UniqueConstraint("course_id", "version", name="uq_course_plans_course_version"),
    )

    course_id: Mapped[str] = mapped_column(
        ForeignKey("course.id"),
        nullable=False,
        index=True,
    )

    rps_analysis_id: Mapped[str] = mapped_column(
        ForeignKey("rps_analyses.id"),
        nullable=False,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    status: Mapped[CoursePlanStatus] = mapped_column(
        Enum(CoursePlanStatus, name="course_plan_status"),
        nullable=False,
        default=CoursePlanStatus.DRAFT,
    )

    plan_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    generated_by_agent_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.id"),
        nullable=True,
    )
