import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class InstructorProfile(BaseModel):
    __tablename__ = "instructor_profiles"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
    )

    teaching_style: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    language: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    content_preferences: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    activity_preferences: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    additional_preferences: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
