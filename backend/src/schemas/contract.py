"""DTO kontrak endpoint workflow yang belum diimplementasikan (BE-06.4).

Endpoint pada modul ini **belum ada implementasinya**. Tujuannya satu: membuat
bentuk request/response terlihat pada OpenAPI (``/docs``) supaya frontend dapat
membangun halaman beserta mock sebelum endpoint-nya selesai (design-api §16,
§17). Rute stub-nya ada di :mod:`src.routes.contract`.

Semua DTO dikumpulkan pada satu modul agar mudah dihapus: begitu BE-11.3
(workflow & event) mengimplementasikan endpoint-nya, model di sini dipindahkan ke
modul schema fitur masing-masing dan rute stub-nya dibuang. Setup dosen (§7)
sudah dipindahkan ke :mod:`src.schemas.instructor` oleh BE-10.2; reanalyze RPS
(§6.6) oleh BE-08.2 dan daftar/hasil analisis RPS (§6.4–§6.5) oleh BE-08.3
dipindahkan ke :mod:`src.schemas.rps`.

Nilai ``role`` mengikuti enum kanonik backend (:class:`src.services.user.UserRole`
— ``INSTRUCTOR``, ``STUDENT``, ``ADMIN``). Pemetaan ke istilah proposal
(``DOSEN``, ``MAHASISWA``) ada pada design-api §5.2 dan
``auth-api-integration.md``; tidak ada nilai role baru di modul ini.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
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


# --- Workflow & event (design-api §16–§17, BE-11.3) ------------------------


class WorkflowStatus(str, Enum):
    """Status workflow orkestrasi (design-api §16)."""

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
                "progress": {"completed": 1, "total": 4},
                "rps_id": RPS_ID_EXAMPLE,
                "created_at": "2026-10-21T08:03:00Z",
                "updated_at": "2026-10-21T08:03:20Z",
            }
        }
    )


class WorkflowResponse(WorkflowSummary):
    """Response ``GET /api/v1/workflows/{workflow_id}`` (design-api §16)."""

    moodle_course_id: int | None = Field(
        default=None,
        description="Course target Moodle; null bila belum dipilih dosen.",
    )


class WorkflowListResponse(BaseModel):
    """Response ``GET /api/v1/workflows`` (design-api §16)."""

    items: list[WorkflowSummary] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": WORKFLOW_ID_EXAMPLE,
                        "status": "RUNNING",
                        "stage": "rps_analysis",
                        "progress": {"completed": 1, "total": 4},
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
    frame WebSocket, sehingga client hanya perlu satu parser. Event tidak pernah
    memuat credential, API key, maupun isi prompt (BE-11.3).
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
                "progress": {"completed": 2, "total": 4},
                "message": "Analisis RPS selesai.",
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
                        "progress": {"completed": 2, "total": 4},
                        "message": "Analisis RPS selesai.",
                        "timestamp": "2026-10-21T08:03:30Z",
                    }
                ]
            }
        }
    )
