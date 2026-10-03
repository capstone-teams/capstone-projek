import enum

from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class ReviewTargetType(str, enum.Enum):
    COURSE_PLAN = "COURSE_PLAN"
    CONTENT = "CONTENT"
    ACTIVITY = "ACTIVITY"


class ReviewDecision(str, enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EDIT_REQUESTED = "EDIT_REQUESTED"


class Review(BaseModel):
    __tablename__ = "reviews"

    reviewer_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # Polymorphic reference (Course Plan / Content / Activity), so
    # intentionally not a single-table foreign key.
    target_type: Mapped[ReviewTargetType] = mapped_column(
        Enum(ReviewTargetType, name="review_target_type"),
        nullable=False,
    )

    target_id: Mapped[str] = mapped_column(
        nullable=False,
        index=True,
    )

    decision: Mapped[ReviewDecision] = mapped_column(
        Enum(ReviewDecision, name="review_decision"),
        nullable=False,
    )

    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
