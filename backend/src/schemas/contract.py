"""DTO kontrak endpoint Sprint yang belum diimplementasikan (BE-06.4).

Endpoint pada modul ini **belum ada implementasinya**. Tujuannya satu: membuat
bentuk request/response terlihat pada OpenAPI (``/docs``) supaya frontend dapat
membangun halaman beserta mock sebelum endpoint-nya selesai (design-api §6.4,
§6.5, §16, §17). Rute stub-nya ada di :mod:`src.routes.contract`.

Semua DTO dikumpulkan pada satu modul agar mudah dihapus: begitu BE-08.3
(daftar & analisis RPS) dan BE-11.3 (workflow & event) mengimplementasikan
endpoint-nya, model di sini dipindahkan ke modul schema fitur masing-masing dan
rute stub-nya dibuang. Setup dosen (§7) sudah dipindahkan ke
:mod:`src.schemas.instructor` oleh BE-10.2; reanalyze RPS (§6.6) sudah
dipindahkan ke :mod:`src.schemas.rps` oleh BE-08.2.

Nilai ``role`` mengikuti enum kanonik backend (:class:`src.services.user.UserRole`
— ``INSTRUCTOR``, ``STUDENT``, ``ADMIN``). Pemetaan ke istilah proposal
(``DOSEN``, ``MAHASISWA``) ada pada design-api §5.2 dan
``auth-api-integration.md``; tidak ada nilai role baru di modul ini.

Hasil analisis RPS **tidak** diduplikasi di sini: ``RPSAnalysisResponse.data``
memakai :class:`~src.schemas.rps_structured.RPSStructuredData` (BE-05.3), schema
yang juga menjadi bentuk kolom ``rps.structured_data`` (BE-08.2).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.rps_structured import RPSStructuredData
from src.services.rps.enums import RPSStatus

__all__ = [
    "RPSAnalysisResponse",
    "RPSListItem",
    "RPSListResponse",
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


# --- RPS (design-api §6.4–§6.6, BE-08.3) -----------------------------------


class RPSListItem(BaseModel):
    """Satu baris daftar RPS milik dosen yang login (design-api §6.5).

    ``workflow_id`` baru terisi setelah BE-11.2 menghubungkan RPS dengan
    workflow analisisnya; sebelum itu nilainya ``null``.
    """

    id: str
    filename: str
    status: RPSStatus
    schema_version: str
    workflow_id: str | None = Field(
        default=None,
        description="Workflow analisis RPS ini; null bila belum ada (BE-11.2).",
    )
    has_source_document: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": RPS_ID_EXAMPLE,
                "filename": "rps-basis-data.pdf",
                "status": "PROCESSED",
                "schema_version": "2.0",
                "workflow_id": None,
                "has_source_document": True,
                "created_at": "2026-10-21T08:00:00Z",
                "updated_at": "2026-10-21T08:00:42Z",
            }
        }
    )


class RPSListResponse(BaseModel):
    """Response ``GET /api/v1/rps`` (design-api §6.5)."""

    items: list[RPSListItem] = Field(default_factory=list, description="RPS milik dosen.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": RPS_ID_EXAMPLE,
                        "filename": "rps-basis-data.pdf",
                        "status": "PROCESSED",
                        "schema_version": "2.0",
                        "workflow_id": None,
                        "has_source_document": True,
                        "created_at": "2026-10-21T08:00:00Z",
                        "updated_at": "2026-10-21T08:00:42Z",
                    }
                ]
            }
        }
    )


class RPSAnalysisResponse(BaseModel):
    """Response ``GET /api/v1/rps/{rps_id}/analysis`` (design-api §6.4).

    ``data`` adalah RPS Structured Data lengkap (content-schema §6.2) — identitas
    mata kuliah, CPL, CPMK, Sub-CPMK, rencana mingguan, penilaian, dan referensi.
    """

    rps_id: str
    analyzed_at: datetime = Field(description="Waktu analisis yang menghasilkan data ini.")
    data: RPSStructuredData

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rps_id": RPS_ID_EXAMPLE,
                "analyzed_at": "2026-10-21T08:01:10Z",
                "data": {
                    "schema_version": "2.0",
                    "course": {"name": "Basis Data", "code": "IF123", "credits": 3},
                    "cpmk": [{"id": "CPMK-1", "description": "Merancang basis data relasional"}],
                    "weeks": [{"week": 1, "topics": ["Pengenalan Basis Data"]}],
                },
            }
        }
    )


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
