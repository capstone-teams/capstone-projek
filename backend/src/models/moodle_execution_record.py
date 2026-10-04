from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class MoodleExecutionRecord(BaseModel):
    __tablename__ = "moodle_executions"
    __table_args__ = (Index("ix_moodle_executions_entity", "entity_type", "internal_id"),)

    operation: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    internal_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    moodle_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)