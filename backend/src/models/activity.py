"""Entity Activity — satu versi assignment/quiz hasil generation (BE-19.1).

Tabel ``activities`` menyimpan dua jenis konten yang dipetakan BE-20.1 ke
aktivitas Moodle (``ASSIGNMENT`` dan ``QUIZ``). Aturan versi dan identitasnya
sama dengan :mod:`src.models.content`: ``content_key`` tetap antarversi dan
regenerasi menambah baris dengan nomor ``version`` berikutnya.
"""

import enum

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class ActivityType(str, enum.Enum):
    ASSIGNMENT = "ASSIGNMENT"
    QUIZ = "QUIZ"


class ActivityStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"


class Activity(BaseModel):
    __tablename__ = "activities"
    __table_args__ = (
        # Satu nomor versi hanya boleh muncul sekali untuk satu content key.
        # Baris lama (content_key NULL) tetap valid karena NULL tidak bentrok.
        UniqueConstraint(
            "content_key", "version", name="uq_activities_content_key_version"
        ),
        Index("ix_activities_workflow_week", "workflow_id", "week_number"),
    )

    workflow_id: Mapped[str | None] = mapped_column(
        ForeignKey("workflows.id"),
        nullable=True,
        index=True,
    )

    course_plan_id: Mapped[str | None] = mapped_column(
        ForeignKey("course_plans.id"),
        nullable=True,
        index=True,
    )

    course_plan_week_id: Mapped[str] = mapped_column(
        ForeignKey("course_plan_weeks.id"),
        nullable=False,
        index=True,
    )

    # Nomor minggu, disalin dari rencana minggu saat konten disimpan.
    week_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Identitas konten yang tetap sama antarversi (Content Schema §22).
    content_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
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

    # Catatan dosen saat menolak versi ini; dipakai sebagai konteks regenerasi.
    revision_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Jejak agent: prompt dan model yang menghasilkan versi ini (BE-19.1).
    prompt_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    model_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    generated_by_agent_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.id"),
        nullable=True,
    )
