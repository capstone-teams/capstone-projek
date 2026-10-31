"""DTO monitoring workflow (BE-11.3).

Kontrak mengikuti ``docs/02. design/design-api.md`` §16–§17 (diterbitkan pada
BE-06.4, diimplementasikan di sini):

- ``GET /api/v1/workflows`` — daftar workflow milik dosen yang login;
- ``GET /api/v1/workflows/{workflow_id}`` — status beserta course target Moodle;
- ``GET /api/v1/workflows/{workflow_id}/events`` — riwayat event;
- ``PUT /api/v1/workflows/{workflow_id}/moodle-target`` — simpan course target
  (issue BE-11.3, proposal §3.4.7);
- ``WS /api/v1/ws/workflows/{workflow_id}`` — frame event real-time, memakai
  bentuk ``WorkflowEvent`` yang sama dengan riwayat HTTP.

Nilai ``WorkflowStatus`` pada modul ini adalah **status lifecycle API**
(``QUEUED``/``RUNNING``/``COMPLETED``/``FAILED``), hasil pemetaan dari state
machine internal (``src.models.workflow.WorkflowStatus``). Status tahap internal
tidak bocor ke kontrak; tahap aktif dibaca dari field ``stage`` (design-api §16).

Semua response hanya memuat data workflow milik dosen yang login. Event tidak
pernah memuat credential, API key, isi prompt, maupun metadata sensitif
(design-api §23).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "MoodleTargetRequest",
    "WorkflowEvent",
    "WorkflowEventListResponse",
    "WorkflowListResponse",
    "WorkflowProgress",
    "WorkflowResponse",
    "WorkflowStatus",
    "WorkflowSummary",
]

RPS_ID_EXAMPLE = "kP3nQ7vRtYx2bM8sLdWfZa"
WORKFLOW_ID_EXAMPLE = "q7RtYx2bM8sLdWfZaKp3nQ"


class WorkflowStatus(str, Enum):
    """Status lifecycle workflow yang dilaporkan API (design-api §16)."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class WorkflowProgress(BaseModel):
    """Kemajuan langkah workflow; ``total`` 0 berarti jumlahnya belum diketahui."""

    completed: int = Field(default=0, ge=0)
    total: int = Field(default=0, ge=0)

    model_config = ConfigDict(json_schema_extra={"example": {"completed": 4, "total": 16}})


class WorkflowSummary(BaseModel):
    """Satu workflow pada daftar ``GET /api/v1/workflows`` (design-api §16)."""

    id: str
    status: WorkflowStatus
    stage: str | None = Field(default=None, description="Tahap yang sedang berjalan.")
    progress: WorkflowProgress = Field(default_factory=WorkflowProgress)
    rps_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": WORKFLOW_ID_EXAMPLE,
                "status": "RUNNING",
                "stage": "rps_analysis",
                "progress": {"completed": 1, "total": 2},
                "rps_id": RPS_ID_EXAMPLE,
                "created_at": "2026-10-21T08:03:00Z",
                "updated_at": "2026-10-21T08:03:20Z",
            }
        }
    )


class WorkflowResponse(WorkflowSummary):
    """Response detail dan update workflow (design-api §16.2)."""

    moodle_course_id: int | None = Field(
        default=None,
        description="Course target Moodle; null bila belum dipilih dosen.",
    )


class WorkflowListResponse(BaseModel):
    """Response ``GET /api/v1/workflows`` (design-api §16.1)."""

    items: list[WorkflowSummary] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": WORKFLOW_ID_EXAMPLE,
                        "status": "RUNNING",
                        "stage": "rps_analysis",
                        "progress": {"completed": 1, "total": 2},
                        "rps_id": RPS_ID_EXAMPLE,
                        "created_at": "2026-10-21T08:03:00Z",
                        "updated_at": "2026-10-21T08:03:20Z",
                    }
                ]
            }
        }
    )


class WorkflowEvent(BaseModel):
    """Satu event workflow (design-api §17, ``WS /api/v1/ws/workflows/{workflow_id}``).

    Bentuk yang sama dipakai riwayat ``GET /api/v1/workflows/{id}/events`` dan
    frame WebSocket, sehingga client hanya perlu satu parser.
    """

    event: str = Field(description="Nama event, contoh: ``WORKFLOW_STAGE_STARTED``.")
    workflow_id: str
    stage: str | None = None
    progress: WorkflowProgress | None = None
    message: str | None = Field(default=None, description="Ringkasan aman ditampilkan.")
    timestamp: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event": "WORKFLOW_STAGE_COMPLETED",
                "workflow_id": WORKFLOW_ID_EXAMPLE,
                "stage": "rps_analysis",
                "progress": {"completed": 2, "total": 2},
                "message": "Tahap analisis RPS selesai.",
                "timestamp": "2026-10-21T08:03:30Z",
            }
        }
    )


class WorkflowEventListResponse(BaseModel):
    """Response ``GET /api/v1/workflows/{workflow_id}/events`` (design-api §17)."""

    items: list[WorkflowEvent] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "event": "WORKFLOW_STAGE_COMPLETED",
                        "workflow_id": WORKFLOW_ID_EXAMPLE,
                        "stage": "rps_analysis",
                        "progress": {"completed": 2, "total": 2},
                        "message": "Tahap analisis RPS selesai.",
                        "timestamp": "2026-10-21T08:03:30Z",
                    }
                ]
            }
        }
    )


class MoodleTargetRequest(BaseModel):
    """Body ``PUT /api/v1/workflows/{workflow_id}/moodle-target`` (issue BE-11.3).

    ``moodle_course_id`` wajib dikirim: bilangan positif untuk memilih course
    atau ``null`` untuk mengosongkan target. Body ``{}`` ditolak agar
    pengosongan tidak terjadi karena field yang terlupa.
    """

    moodle_course_id: int | None = Field(
        ...,
        ge=1,
        description="Identifier course Moodle; null mengosongkan target.",
    )

    model_config = ConfigDict(
        json_schema_extra={"example": {"moodle_course_id": 42}}
    )
