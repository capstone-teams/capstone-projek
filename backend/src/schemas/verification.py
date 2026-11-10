"""DTO Moodle verification berbasis workflow (BE-22.2).

Endpoint ``/workflows/{workflow_id}/verifications`` menggantikan endpoint
verifikasi berbasis course pada API Specification §14. Hasil verifikasi berasal
dari :class:`~src.services.verification.service.VerificationService` (BE-21.2):
status, perbedaan yang tersisa, perbedaan yang berhasil diperbaiki, jumlah
perbaikan, dan waktu. Response tidak pernah memuat credential Moodle maupun
payload mentah web service.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "DiscrepancyResponse",
    "DiscrepancyType",
    "VerificationCreateRequest",
    "VerificationListResponse",
    "VerificationResponse",
    "VerificationStatus",
]

WORKFLOW_ID_EXAMPLE = "q7RtYx2bM8sLdWfZaKp3nQ"
EXECUTION_ID_EXAMPLE = "Xa9bC2dE4fG6hJ8kLm3nP"
VERIFICATION_ID_EXAMPLE = "Vr5tY7uJ9oP2aS4dF6gHjK"


class VerificationStatus(str, Enum):
    """Hasil verifikasi.

    ``PASS``: course sesuai rencana. ``PARTIAL``: hanya ada activity tambahan
    yang tidak berasal dari eksekusi. ``FAIL``: masih ada perbedaan setelah
    perbaikan. ``UNKNOWN``: Moodle tidak dapat dibaca.
    """

    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class DiscrepancyType(str, Enum):
    """Jenis perbedaan antara rencana yang disetujui dan isi course Moodle."""

    MISSING = "MISSING"
    WRONG_SECTION = "WRONG_SECTION"
    TITLE_MISMATCH = "TITLE_MISMATCH"
    UNEXPECTED = "UNEXPECTED"
    MAPPING_MISMATCH = "MAPPING_MISMATCH"


class DiscrepancyResponse(BaseModel):
    """Satu perbedaan hasil verifikasi; aman ditampilkan ke dosen."""

    type: DiscrepancyType
    label: str = Field(description="Label singkat jenis perbedaan, mis. `hilang`.")
    target: str = Field(
        description="`SECTION`, jenis operasi konten (mis. `QUIZ`), atau `ACTIVITY` untuk module tidak terduga."
    )
    week_number: int | None = None
    message: str
    expected: dict[str, Any] = Field(default_factory=dict)
    actual: dict[str, Any] = Field(default_factory=dict)
    operation_id: str | None = Field(
        default=None, description="Operasi eksekusi terkait; null untuk activity tidak terduga."
    )
    moodle_object_id: int | None = None
    repairable: bool = Field(
        description="Dapat diperbaiki dengan menjalankan ulang operasi eksekusi terkait."
    )


class VerificationCreateRequest(BaseModel):
    """Body opsional ``POST /api/v1/workflows/{workflow_id}/verifications``.

    Tanpa ``execution_id``, eksekusi ``FULL`` terakhir yang sudah selesai yang
    diverifikasi.
    """

    execution_id: str | None = Field(
        default=None, description="Eksekusi yang diverifikasi; kosongkan untuk eksekusi FULL terakhir."
    )

    model_config = ConfigDict(json_schema_extra={"example": {}})


class VerificationResponse(BaseModel):
    """Satu hasil verifikasi course hasil eksekusi."""

    verification_id: str
    workflow_id: str
    execution_id: str
    status: VerificationStatus
    matches: bool = Field(description="True bila status `PASS`.")
    summary: dict[str, int] | None = Field(
        default=None,
        description="Jumlah section dan activity yang diharapkan dan ditemukan.",
    )
    discrepancies: list[DiscrepancyResponse] = Field(
        default_factory=list, description="Perbedaan yang masih ada setelah perbaikan."
    )
    repaired: list[DiscrepancyResponse] = Field(
        default_factory=list, description="Perbedaan yang berhasil diperbaiki otomatis."
    )
    repair_count: int = Field(default=0, ge=0, description="Jumlah operasi yang dijalankan ulang.")
    repair_rounds: int = Field(default=0, ge=0)
    error_message: str | None = Field(
        default=None, description="Pesan publik bila Moodle tidak dapat dibaca (`UNKNOWN`)."
    )
    verified_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "verification_id": VERIFICATION_ID_EXAMPLE,
                "workflow_id": WORKFLOW_ID_EXAMPLE,
                "execution_id": EXECUTION_ID_EXAMPLE,
                "status": "PARTIAL",
                "matches": False,
                "summary": {
                    "expected_sections": 16,
                    "actual_sections": 16,
                    "expected_activities": 4,
                    "found_activities": 4,
                },
                "discrepancies": [
                    {
                        "type": "UNEXPECTED",
                        "label": "tidak terduga",
                        "target": "ACTIVITY",
                        "week_number": 2,
                        "message": "Module forum 'Diskusi Minggu 2' tidak berasal dari eksekusi.",
                        "expected": {},
                        "actual": {"title": "Diskusi Minggu 2", "modname": "forum", "section": 2},
                        "operation_id": None,
                        "moodle_object_id": 340,
                        "repairable": False,
                    }
                ],
                "repaired": [
                    {
                        "type": "MISSING",
                        "label": "hilang",
                        "target": "LEARNING_MATERIAL",
                        "week_number": 1,
                        "message": "LEARNING_MATERIAL minggu 1 tidak ada di course (kemungkinan dihapus dari Moodle).",
                        "expected": {"title": "Konsep Basis Data Relasional", "modname": "page"},
                        "actual": {},
                        "operation_id": "Op3sT4uV6wX8yZ1aB3cDf",
                        "moodle_object_id": 311,
                        "repairable": True,
                    }
                ],
                "repair_count": 1,
                "repair_rounds": 1,
                "error_message": None,
                "verified_at": "2026-11-08T08:05:00Z",
            }
        }
    )


class VerificationListResponse(BaseModel):
    """Riwayat verifikasi sebuah workflow, terbaru lebih dulu."""

    items: list[VerificationResponse] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "verification_id": VERIFICATION_ID_EXAMPLE,
                        "workflow_id": WORKFLOW_ID_EXAMPLE,
                        "execution_id": EXECUTION_ID_EXAMPLE,
                        "status": "PASS",
                        "matches": True,
                        "summary": {
                            "expected_sections": 16,
                            "actual_sections": 16,
                            "expected_activities": 4,
                            "found_activities": 4,
                        },
                        "discrepancies": [],
                        "repaired": [],
                        "repair_count": 0,
                        "repair_rounds": 0,
                        "error_message": None,
                        "verified_at": "2026-11-08T08:05:00Z",
                    }
                ]
            }
        }
    )