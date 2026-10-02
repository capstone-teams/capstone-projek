
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class RPSAnalysis(BaseModel):
    __tablename__ = "rps_analyses"

    rps_id: Mapped[str] = mapped_column(
        ForeignKey("rps.id"),
        nullable=False,
        index=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    course_identity: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    learning_outcomes: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    objectives: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    topics: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    weekly_distribution: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    teaching_methods: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    assessments: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Note: "references" shadows the Python builtin word loosely used in the
    # doc's table; renamed to `references_data` to avoid confusion with SQLA's
    # relationship "references" terminology. Adjust the column name back to
    # "references" if the DB schema must match the doc's field name exactly.
    references_data: Mapped[dict | None] = mapped_column(
        "references",
        JSONB,
        nullable=True,
    )

    raw_analysis: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
