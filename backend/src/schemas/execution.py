"""DTO eksekusi Moodle berbasis workflow (BE-17.2).

Kontrak mengikuti issue BE-17.2 dan DL-012: endpoint eksekusi berbasis
``/workflows/{workflow_id}/executions`` menggantikan endpoint
``/courses/{course_id}/execute`` pada API Specification §13.1–§13.2.

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
    """Cakupan eksekusi (DL-012). M03 baru mengimplementasikan ``STRUCTURE``."""

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

    ``scope`` wajib berupa ``STRUCTURE`` pada M03; cakupan ``FULL`` menyusul pada
    M04 (DL-012).
    """

    scope: ExecutionScope = ExecutionScope.STRUCTURE

    model_config = ConfigDict(json_schema_extra={"example": {"scope": "STRUCTURE"}})


class ExecutionOperationResponse(BaseModel):
    """Satu operasi mingguan beserta hasilnya (issue BE-17.2)."""

    operation_id: str
    operation_type: OperationType
    status: OperationStatus
    idempotency_key: str
    week_number: int | None = Field(
        default=None, description="Nomor minggu course plan; null untuk operasi non-mingguan."
    )
    moodle_object_id: str | None = Field(
        default=None, description="ID objek Moodle hasil operasi, mis. ID section."
    )
    error_message: str | None = Field(
        default=None, description="Pesan publik untuk operasi yang gagal."
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
    """Detail eksekusi: ringkasan, operasi per minggu, dan hasil read-back."""

    readback: dict | None = Field(
        default=None,
        description=(
            "Hasil read-back struktur course dari Moodle: jumlah section, urutan, "
            "dan nama yang cocok dengan course plan."
        ),
    )
    operations: list[ExecutionOperationResponse] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "execution_id": EXECUTION_ID_EXAMPLE,
                "workflow_id": WORKFLOW_ID_EXAMPLE,
                "course_plan_id": COURSE_PLAN_ID_EXAMPLE,
                "scope": "STRUCTURE",
                "status": "FAILED",
                "moodle_course_id": 42,
                "summary": {"total": 16, "success": 15, "failed": 1, "skipped": 0},
                "error_message": "1 operasi gagal diterapkan ke Moodle.",
                "created_at": "2026-11-08T08:00:00Z",
                "started_at": "2026-11-08T08:00:01Z",
                "completed_at": "2026-11-08T08:00:20Z",
                "readback": {
                    "checked": True,
                    "matches": False,
                    "expected_sections": 16,
                    "actual_sections": 16,
                    "ordered": True,
                    "missing_weeks": [],
                    "mismatched_weeks": [4],
                },
                "operations": [
                    {
                        "operation_id": "Op2sT4uV6wX8yZ1aB3cDe",
                        "operation_type": "SECTION",
                        "status": "SUCCESS",
                        "idempotency_key": f"{WORKFLOW_ID_EXAMPLE}:week:1:SECTION",
                        "week_number": 1,
                        "moodle_object_id": "201",
                        "error_message": None,
                        "retry_count": 0,
                    },
                    {
                        "operation_id": "Op3sT4uV6wX8yZ1aB3cDf",
                        "operation_type": "SECTION",
                        "status": "FAILED",
                        "idempotency_key": f"{WORKFLOW_ID_EXAMPLE}:week:4:SECTION",
                        "week_number": 4,
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
