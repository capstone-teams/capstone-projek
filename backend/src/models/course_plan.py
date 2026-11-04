"""Entity CoursePlan (BE-14.1).

Satu baris ``course_plans`` adalah **satu versi** rencana pembelajaran hasil
agent untuk sebuah workflow. Versi tidak pernah ditimpa: regenerasi menambah
baris baru dengan ``version`` berikutnya, sehingga riwayat penolakan dan
regenerasi tetap dapat ditelusuri (proposal §3.5.2, DL-012).

Status approval mengikuti issue BE-14.1 — ``DRAFT``, ``APPROVED``, dan
``REJECTED``. ``VALIDATED``/``PENDING_REVIEW`` dipertahankan untuk baris lama
yang dibuat sebelum alur review berbasis workflow (BE-14.2); alur baru tidak
pernah menulis keduanya.

``workflow_id`` dan ``rps_id`` boleh kosong hanya untuk baris lama yang dibuat
sebelum BE-14 (alur berbasis course). Service BE-14 selalu mengisinya.

Hanya satu versi berstatus ``APPROVED`` per workflow. Aturan itu dijaga
repository/service, dan dijaga lagi oleh database lewat partial unique index
``uq_course_plans_workflow_approved`` supaya dua penulis tidak dapat melanggar
secara bersamaan.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class CoursePlanStatus(str, enum.Enum):
    """Status approval satu versi course plan (issue BE-14.1)."""

    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class CoursePlan(BaseModel):
    __tablename__ = "course_plans"
    __table_args__ = (
        # Versi unik per course (alur lama) dan per workflow (alur BE-14).
        # Kolom yang NULL tidak saling bentrok pada PostgreSQL, sehingga baris
        # lama tanpa workflow tidak menghalangi versi workflow baru.
        UniqueConstraint("course_id", "version", name="uq_course_plans_course_version"),
        UniqueConstraint(
            "workflow_id", "version", name="uq_course_plans_workflow_version"
        ),
        Index(
            "uq_course_plans_workflow_approved",
            "workflow_id",
            unique=True,
            postgresql_where=text("status = 'APPROVED'"),
            sqlite_where=text("status = 'APPROVED'"),
        ),
        CheckConstraint("weeks_count >= 0", name="ck_course_plans_weeks_count"),
    )

    course_id: Mapped[str | None] = mapped_column(
        ForeignKey("course.id"),
        nullable=True,
        index=True,
    )

    # Workflow pemilik rencana ini; scoping review dan penomoran versi memakai
    # kolom ini (BE-14.2/BE-14.3).
    workflow_id: Mapped[str | None] = mapped_column(
        ForeignKey("workflows.id"),
        nullable=True,
        index=True,
    )

    # RPS yang menjadi sumber akademik rencana (issue BE-14.1).
    rps_id: Mapped[str | None] = mapped_column(
        ForeignKey("rps.id"),
        nullable=True,
        index=True,
    )

    rps_analysis_id: Mapped[str | None] = mapped_column(
        ForeignKey("rps_analyses.id"),
        nullable=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    weeks_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    status: Mapped[CoursePlanStatus] = mapped_column(
        Enum(CoursePlanStatus, name="course_plan_status"),
        nullable=False,
        default=CoursePlanStatus.DRAFT,
    )

    # Snapshot output agent apa adanya (course + weeks), dipakai sebagai konteks
    # regenerasi. Bentuk tervalidasi tiap minggu tetap disimpan juga pada
    # ``course_plan_weeks`` supaya dapat dibaca dan diurutkan lewat query.
    plan_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Preferensi aktivitas dosen saat rencana dibuat (issue BE-14.1); perubahan
    # preferensi setelahnya tidak boleh mengubah riwayat versi lama.
    activity_configuration: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Hasil validasi skema + akademik: ``{"passed": bool, "issues": [...]}``.
    # ``NULL`` berarti versi belum pernah divalidasi (mis. baris lama).
    validation_result: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Catatan penolakan terakhir dan instruksi yang dipakai saat regenerasi.
    revision_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    regeneration_instruction: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Jejak agent: prompt dan model yang menghasilkan versi ini.
    prompt_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    model_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
