import enum

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class ContentType(str, enum.Enum):
    LEARNING_MATERIAL = "LEARNING_MATERIAL"
    RESOURCE = "RESOURCE"


class ContentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Content(BaseModel):
    __tablename__ = "contents"

    course_plan_week_id: Mapped[str] = mapped_column(
        ForeignKey("course_plan_weeks.id"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    content_type: Mapped[ContentType] = mapped_column(
        Enum(ContentType, name="content_type"),
        nullable=False,
    )

    content_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    content_markdown: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, name="content_status"),
        nullable=False,
        default=ContentStatus.DRAFT,
    )

    generated_by_agent_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.id"),
        nullable=True,
    )
