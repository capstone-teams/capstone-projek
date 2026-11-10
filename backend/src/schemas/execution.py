"""DTO eksekusi Moodle berbasis workflow (BE-17.2, BE-22.2).

Kontrak mengikuti issue BE-17.2, BE-22.2, dan DL-012: endpoint eksekusi berbasis
``/workflows/{workflow_id}/executions`` menggantikan endpoint
``/courses/{course_id}/execute`` pada API Specification §13.1–§13.2. Sejak
BE-22.2 cakupan ``FULL`` diterima dan detail eksekusi memuat operasi per konten.

Nilai status di sini adalah status **eksekusi**, bukan status workflow: frontend
membaca status workflow dari §16 dan kemajuan operasi per minggu dari endpoint
ini. Response tidak pernah memuat credential Moodle; pesan error operasi sudah
diterjemahkan menjadi pesan publik yang aman ditampilkan.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ExecutionCreateRequest",
    "ExecutionDetailResponse",
    "ExecutionListResponse",
    "ExecutionOperationResponse",
    "ExecutionResponse",
    "ExecutionScope",
    "ExecutionStatus",
    "ExecutionSummary",
    "OperationStatus",
    "OperationType",
]

WORKFLOW_ID_EXAMPLE = "q7RtYx2bM8sLdWfZaKp3nQ"
EXECUTION_ID_EXAMPLE = "Xa9bC2dE4fG6hJ8kLm3nP"
COURSE_PLAN_ID_EXAMPLE = "Cp7rS9tU2vW4xY6zA8bCd"


class ExecutionScope(str, Enum):
    """Cakupan eksekusi (DL-012): ``STRUCTURE`` (M03) atau ``FULL`` (M04, BE-22.2)."""

    STRUCTURE = "STRUCTURE"
    FULL = "FULL"


class ExecutionStatus(str, Enum):
    """Status satu run eksekusi."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class OperationType(str, Enum):
    """Jenis operasi Moodle yang dicatat sebuah eksekusi."""

    SECTION = "SECTION"
    LEARNING_MATERIAL = "LEARNING_MATERIAL"
    LEARNING_RESOURCE = "LEARNING_RESOURCE"
    ASSIGNMENT = "ASSIGNMENT"
    QUIZ = "QUIZ"


class OperationStatus(str, Enum):
    """Status satu operasi eksekusi."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ExecutionSummary(BaseModel):
    """Ringkasan hasil eksekusi: jumlah operasi per status utama."""

    total: int = Field(default=0, ge=0)
    success: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    skipped: int = Field(default=0, ge=0)

    model_config = ConfigDict(
        json_schema_extra={"example": {"total": 16, "success": 15, "failed": 1, "skipped": 0}}
    )


class ExecutionCreateRequest(BaseModel):
    """Body ``POST /api/v1/workflows/{workflow_id}/executions``.

    ``STRUCTURE`` hanya membuat section mingguan; ``FULL`` membuat section
    beserta seluruh konten ``APPROVED`` (learning material, learning resource,
    assignment, quiz). Jenis konten yang nonaktif atau belum disetujui dicatat
    sebagai operasi ``SKIPPED`` (DL-012, BE-21.1).
    """

    scope: ExecutionScope = ExecutionScope.STRUCTURE

    model_config = ConfigDict(json_schema_extra={"example": {"scope": "FULL"}})


class ExecutionOperationResponse(BaseModel):
    """Satu operasi (section atau konten) beserta hasilnya (BE-17.2, BE-22.2)."""

    operation_id: str
    operation_type: OperationType
    status: OperationStatus
    idempotency_key: str
    week_number: int | None = Field(
        default=None, description="Nomor minggu course plan; null untuk operasi non-mingguan."
    )
    content_id: str | None = Field(
        default=None,
        description="ID versi konten yang dieksekusi; null untuk operasi SECTION dan konten yang dilewati.",
    )
    title: str | None = Field(
        default=None,
        description="Judul konten untuk operasi konten, judul minggu course plan untuk operasi SECTION.",
    )
    moodle_object_id: str | None = Field(
        default=None,
        description="ID objek Moodle hasil operasi: ID section, atau course module ID (cmid) untuk konten.",
    )
    error_message: str | None = Field(
        default=None,
        description="Pesan publik untuk operasi yang gagal, atau alasan operasi SKIPPED.",
    )
    retry_count: int = Field(default=0, ge=0)


class ExecutionResponse(BaseModel):
    """Status ringkas satu eksekusi (response POST, retry, dan item riwayat)."""

    execution_id: str
    workflow_id: str
    course_plan_id: str
    scope: ExecutionScope
    status: ExecutionStatus
    moodle_course_id: int
    summary: ExecutionSummary = Field(default_factory=ExecutionSummary)
    error_message: str | None = Field(
        default=None, description="Pesan publik bila eksekusi gagal."
    )
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "execution_id": EXECUTION_ID_EXAMPLE,
                "workflow_id": WORKFLOW_ID_EXAMPLE,
                "course_plan_id": COURSE_PLAN_ID_EXAMPLE,
                "scope": "STRUCTURE",
                "status": "SUCCESS",
                "moodle_course_id": 42,
                "summary": {"total": 16, "success": 16, "failed": 0, "skipped": 0},
                "error_message": None,
                "created_at": "2026-11-08T08:00:00Z",
                "started_at": "2026-11-08T08:00:01Z",
                "completed_at": "2026-11-08T08:00:20Z",
            }
        }
    )


class ExecutionDetailResponse(ExecutionResponse):
    """Detail eksekusi: ringkasan, operasi per minggu dan per konten, dan read-back."""

    readback: dict | None = Field(
        default=None,
        description=(
            "Hasil read-back course dari Moodle: jumlah section, urutan, nama yang "
            "cocok dengan course plan, dan (FULL) activity per konten."
        ),
    )
    operations: list[ExecutionOperationResponse] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "execution_id": EXECUTION_ID_EXAMPLE,
                "workflow_id": WORKFLOW_ID_EXAMPLE,
                "course_plan_id": COURSE_PLAN_ID_EXAMPLE,
                "scope": "FULL",
                "status": "FAILED",
                "moodle_course_id": 42,
                "summary": {"total": 5, "success": 3, "failed": 1, "skipped": 1},
                "error_message": "1 operasi gagal diterapkan ke Moodle.",
                "created_at": "2026-11-08T08:00:00Z",
                "started_at": "2026-11-08T08:00:01Z",
                "completed_at": "2026-11-08T08:00:40Z",
                "readback": {
                    "checked": True,
                    "matches": True,
                    "expected_sections": 1,
                    "actual_sections": 1,
                    "ordered": True,
                    "missing_weeks": [],
                    "mismatched_weeks": [],
                },
                "operations": [
                    {
                        "operation_id": "Op2sT4uV6wX8yZ1aB3cDe",
                        "operation_type": "SECTION",
                        "status": "SUCCESS",
                        "idempotency_key": f"{WORKFLOW_ID_EXAMPLE}:week:1:SECTION",
                        "week_number": 1,
                        "content_id": None,
                        "title": "Pengantar Basis Data",
                        "moodle_object_id": "201",
                        "error_message": None,
                        "retry_count": 0,
                    },
                    {
                        "operation_id": "Op3sT4uV6wX8yZ1aB3cDf",
                        "operation_type": "LEARNING_MATERIAL",
                        "status": "SUCCESS",
                        "idempotency_key": f"{WORKFLOW_ID_EXAMPLE}:1:LEARNING_MATERIAL",
                        "week_number": 1,
                        "content_id": "Ct4aB2cD3eF4gH5iJ6kL7",
                        "title": "Konsep Basis Data Relasional",
                        "moodle_object_id": "311",
                        "error_message": None,
                        "retry_count": 0,
                    },
                    {
                        "operation_id": "Op4sT4uV6wX8yZ1aB3cDg",
                        "operation_type": "LEARNING_RESOURCE",
                        "status": "SKIPPED",
                        "idempotency_key": f"{WORKFLOW_ID_EXAMPLE}:1:RESOURCE",
                        "week_number": 1,
                        "content_id": None,
                        "title": None,
                        "moodle_object_id": None,
                        "error_message": "Belum ada konten APPROVED untuk jenis ini.",
                        "retry_count": 0,
                    },
                    {
                        "operation_id": "Op5sT4uV6wX8yZ1aB3cDh",
                        "operation_type": "ASSIGNMENT",
                        "status": "SUCCESS",
                        "idempotency_key": f"{WORKFLOW_ID_EXAMPLE}:1:ASSIGNMENT",
                        "week_number": 1,
                        "content_id": "Ct5aB2cD3eF4gH5iJ6kL7",
                        "title": "Tugas 1: Rancangan ERD",
                        "moodle_object_id": "312",
                        "error_message": None,
                        "retry_count": 0,
                    },
                    {
                        "operation_id": "Op6sT4uV6wX8yZ1aB3cDi",
                        "operation_type": "QUIZ",
                        "status": "FAILED",
                        "idempotency_key": f"{WORKFLOW_ID_EXAMPLE}:1:QUIZ",
                        "week_number": 1,
                        "content_id": "Ct6aB2cD3eF4gH5iJ6kL7",
                        "title": "Kuis 1: Konsep Dasar",
                        "moodle_object_id": None,
                        "error_message": "Moodle menolak data yang dikirim.",
                        "retry_count": 0,
                    },
                ],
            }
        }
    )


class ExecutionListResponse(BaseModel):
    """Riwayat eksekusi sebuah workflow, terbaru lebih dulu."""

    items: list[ExecutionResponse] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "execution_id": EXECUTION_ID_EXAMPLE,
                        "workflow_id": WORKFLOW_ID_EXAMPLE,
                        "course_plan_id": COURSE_PLAN_ID_EXAMPLE,
                        "scope": "STRUCTURE",
                        "status": "SUCCESS",
                        "moodle_course_id": 42,
                        "summary": {
                            "total": 16,
                            "success": 16,
                            "failed": 0,
                            "skipped": 0,
                        },
                        "error_message": None,
                        "created_at": "2026-11-08T08:00:00Z",
                        "started_at": "2026-11-08T08:00:01Z",
                        "completed_at": "2026-11-08T08:00:20Z",
                    }
                ]
            }
        }
    )