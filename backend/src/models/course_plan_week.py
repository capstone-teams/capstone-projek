
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class CoursePlanWeek(BaseModel):
    __tablename__ = "course_plan_weeks"
    __table_args__ = (
        UniqueConstraint(
            "course_plan_id", "week_number", name="uq_course_plan_weeks_plan_week"
        ),
    )

    course_plan_id: Mapped[str] = mapped_column(
        ForeignKey("course_plans.id"),
        nullable=False,
        index=True,
    )

    week_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    learning_outcomes: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    topics: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    methods: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    assessment: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )
