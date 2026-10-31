"""Entity Workflow (BE-11.1).

Satu baris ``workflows`` merepresentasikan satu rangkaian pekerjaan agent untuk
sebuah RPS (issue BE-11.1, proposal §3.5.6). Status workflow adalah state
machine yang **hanya** diubah backend/orkestrator (BE-11.2); LLM tidak pernah
menulis kolom ini.

Nilai ``WorkflowStatus`` mengikuti istilah proposal (DL-011): tahap pemrosesan
dan analisis RPS, tahap-tahap lanjutan (planning, generation, Moodle), serta
status lifecycle ``COMPLETED``/``FAILED``/``RETRYING``. ``QUEUED`` adalah satu
nilai tambahan yang dibutuhkan kontrak API (design-api §16: status workflow
``QUEUED``/``RUNNING``/``COMPLETED``/``FAILED``) untuk workflow yang sudah
dibuat tetapi belum mulai dikerjakan.

``moodle_course_id`` menyimpan course target Moodle pada workflow (issue
BE-11.3, proposal §3.4.7) dan boleh kosong sampai dosen memilih course.

``progress_completed``/``progress_total`` menyimpan kemajuan tahap yang
ditampilkan API monitoring (design-api §16). Nilainya dihitung orkestrator,
bukan client.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class WorkflowStatus(str, enum.Enum):
    """Status workflow orkestrasi (issue BE-11.1, design-api §20)."""

    # Workflow sudah dibuat dan menunggu orkestrator mengambilnya.
    QUEUED = "QUEUED"

    # Tahap pekerjaan agent. Selama salah satu nilai ini aktif, API melaporkan
    # status ``RUNNING`` beserta nama tahapnya (design-api §16).
    PROCESSING_RPS = "PROCESSING_RPS"
    ANALYZING_RPS = "ANALYZING_RPS"
    PLANNING_COURSE = "PLANNING_COURSE"
    GENERATING_CONTENT = "GENERATING_CONTENT"
    VALIDATING = "VALIDATING"
    WAITING_FOR_REVIEW = "WAITING_FOR_REVIEW"
    EXECUTING_TO_MOODLE = "EXECUTING_TO_MOODLE"
    VERIFYING = "VERIFYING"

    # Tahap gagal tetapi masih ada jatah percobaan ulang.
    RETRYING = "RETRYING"

    # Status akhir.
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Workflow(BaseModel):
    __tablename__ = "workflows"

    # Dosen pemilik workflow. Seluruh endpoint monitoring hanya menampilkan
    # workflow milik dosen yang login (design-api §16).
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # RPS yang dikerjakan workflow ini (issue BE-11.1). Satu RPS boleh memiliki
    # beberapa workflow historis, sehingga kolomnya tidak unik; workflow aktif
    # terakhir juga dicatat pada ``rps.workflow_id``.
    rps_id: Mapped[str] = mapped_column(
        ForeignKey("rps.id"),
        nullable=False,
        index=True,
    )

    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus, name="workflow_status"),
        nullable=False,
        default=WorkflowStatus.QUEUED,
        server_default=WorkflowStatus.QUEUED.value,
        index=True,
    )

    # Course target Moodle (design-api §16.2, proposal §3.4.7). NULL berarti
    # dosen belum memilih course.
    moodle_course_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Model LLM yang dipakai workflow ini, dicatat untuk audit (issue BE-11.1).
    model_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Kemajuan tahap: ``completed`` dari ``total`` tahap pada run terakhir.
    progress_completed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    progress_total: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    # Waktu run pertama dimulai dan waktu status akhir tercapai.
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
