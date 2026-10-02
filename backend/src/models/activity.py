import enum

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class ActivityType(str, enum.Enum):
    ASSIGNMENT = "ASSIGNMENT"
    QUIZ = "QUIZ"


class ActivityStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    EXECUTED = "EXECUTED"


class Activity(BaseModel):
    __tablename__ = "activities"

    course_plan_week_id: Mapped[str] = mapped_column(
        ForeignKey("course_plan_weeks.id"),
        nullable=False,
        index=True,
    )

    type: Mapped[ActivityType] = mapped_column(
        "type",
        Enum(ActivityType, name="activity_type"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    activity_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    status: Mapped[ActivityStatus] = mapped_column(
        Enum(ActivityStatus, name="activity_status"),
        nullable=False,
        default=ActivityStatus.DRAFT,
    )
