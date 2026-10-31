"""Entity WorkflowEvent (BE-11.1).

Event adalah catatan audit dan monitoring satu kejadian di dalam workflow
(design-api §16.3/§17; data-model §16 versi Workflow). Event **tidak boleh**
memuat credential, API key, isi prompt, maupun hidden chain-of-thought — field
``metadata`` hanya untuk data non-sensitif yang aman ditampilkan.

Dua penanda event disimpan bersamaan karena melayani dua kontrak yang berbeda:

- ``event_type`` — kategori menurut istilah proposal (DL-011): perubahan tahap,
  aktivitas agent, operasi Moodle, retry, dan kegagalan (issue BE-11.1);
- ``event`` — nama event publik berpola ``WORKFLOW_*`` yang menjadi kontrak
  event history HTTP dan frame WebSocket (design-api §17).

Memisahkan keduanya membuat kategori audit tetap stabil walaupun client
membutuhkan nama event yang lebih spesifik (mis. ``WORKFLOW_RETRY``).
"""

import enum

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class EventType(str, enum.Enum):
    """Kategori event workflow (issue BE-11.1, DL-011)."""

    PERUBAHAN_TAHAP = "PERUBAHAN_TAHAP"
    AKTIVITAS_AGENT = "AKTIVITAS_AGENT"
    OPERASI_MOODLE = "OPERASI_MOODLE"
    RETRY_FIX = "RETRY_FIX"
    ERROR_FAILURE = "ERROR_FAILURE"


class WorkflowEvent(BaseModel):
    __tablename__ = "workflow_events"

    workflow_id: Mapped[str] = mapped_column(
        ForeignKey("workflows.id"),
        nullable=False,
        index=True,
    )

    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, name="workflow_event_type"),
        nullable=False,
    )

    # Nama event publik (``WORKFLOW_STARTED``, ``WORKFLOW_STAGE_STARTED``, ...).
    # Bentuk yang sama dipakai ``GET /workflows/{id}/events`` dan frame
    # WebSocket (design-api §17), sehingga client cukup memakai satu parser.
    event: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    stage: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Metadata non-sensitif (mis. attempt, reason_code, progress). Nama atribut
    # diberi garis bawah karena ``metadata`` adalah nama terpakai SQLAlchemy.
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )
