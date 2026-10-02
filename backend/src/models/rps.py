import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class RPSStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class RPS(BaseModel):
    __tablename__ = "rps"

    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    file_path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )

    file_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    status: Mapped[RPSStatus] = mapped_column(
        Enum(RPSStatus, name="rps_status"),
        nullable=False,
        default=RPSStatus.UPLOADED,
        index=True,
    )

    source_markdown: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    structured_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
