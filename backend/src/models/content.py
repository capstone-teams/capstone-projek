"""Entity Content — satu versi konten hasil generation (BE-19.1).

Satu baris ``contents`` adalah **satu versi** dari satu konten. Konten yang
sama antarversi diikat oleh ``content_key``; regenerasi menambah baris baru
dengan nomor ``version`` berikutnya dan tidak mengubah versi lama.

Jenis konten yang disimpan di tabel ini mengikuti Content Output Schema
(BE-20.1): ``LEARNING_MATERIAL`` dan ``RESOURCE``. ``ASSIGNMENT`` dan ``QUIZ``
disimpan pada tabel ``activities`` (lihat ``src.models.activity``), sesuai
pemetaan ``src.schemas.content.REGISTRY``.

Kolom ``workflow_id``/``course_plan_id``/``week_number`` didenormalisasi dari
``course_plan_weeks`` supaya endpoint review (BE-19.2) dapat memfilter konten
per workflow dan per minggu tanpa join berlapis, dan supaya identitas konten
tidak hilang bila rencana minggu dibaca ulang.
"""

import enum

from sqlalchemy import (
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
    __table_args__ = (
        # Satu nomor versi hanya boleh muncul sekali untuk satu content key.
        # Baris lama (content_key NULL) tetap valid karena NULL tidak bentrok.
        UniqueConstraint(
            "content_key", "version", name="uq_contents_content_key_version"
        ),
        Index("ix_contents_workflow_week", "workflow_id", "week_number"),
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
