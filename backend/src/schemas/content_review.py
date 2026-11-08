"""DTO endpoint review konten hasil generation (BE-19.2).

Bentuknya mengikuti Sequence Diagram Review Generated Content (Proposal
§3.4.6): daftar konten per minggu/jenis, detail versi terbaru beserta hasil
validasi, riwayat versi, dan keputusan dosen.

``ContentDetail`` sama untuk keempat jenis konten; isi ``content_data`` yang
berbeda mengikuti Content Output Schema (BE-20.1). Contoh response keempat
jenis ada di :data:`CONTENT_DETAIL_EXAMPLES` dan dipakai pada dokumentasi
OpenAPI.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.models.validation_result import ValidationStatus
from src.services.content.domain import ApprovalStatus, ContentKind

__all__ = [
    "CONTENT_DETAIL_EXAMPLES",
    "ContentApproveRequest",
    "ContentDecisionResponse",
    "ContentDetail",
    "ContentListResponse",
    "ContentRejectRequest",
    "ContentSelection",
    "ContentSummary",
    "ContentValidationDetail",
    "ContentValidationSummary",
    "ContentVersionListResponse",
    "ContentVersionSummary",
]


class ContentValidationSummary(BaseModel):
    """Ringkasan hasil validasi yang ikut pada setiap item daftar."""

    status: ValidationStatus
    score: float | None = None
    retry_count: int = 0
    validated_at: datetime | None = None


class ContentValidationDetail(ContentValidationSummary):
    """Hasil validasi lengkap beserta temuan (detail satu versi)."""

    checks: dict | None = None
    errors: dict | None = None
    warnings: dict | None = None
    created_at: datetime | None = None


class ContentSummary(BaseModel):
    """Satu baris daftar konten (versi terbaru sebuah ``content_key``)."""

    id: str
    content_key: str
    kind: ContentKind
    week_number: int | None = None
    title: str
    version: int
    status: ApprovalStatus
    revision_notes: str | None = None
    validation: ContentValidationSummary | None = None
    created_at: datetime
    updated_at: datetime


class ContentDetail(ContentSummary):
    """Detail satu versi konten beserta isi dan hasil validasi lengkap."""

    workflow_id: str | None = None
    course_plan_id: str | None = None
    course_plan_week_id: str
    content_data: dict | None = None
    content_markdown: str | None = None
    prompt_version: str | None = None
    model_name: str | None = None
    validation: ContentValidationDetail | None = None


class ContentListResponse(BaseModel):
    """Daftar konten satu workflow."""

    items: list[ContentSummary]


class ContentVersionSummary(BaseModel):
    """Satu baris riwayat versi konten."""

    id: str
    version: int
    status: ApprovalStatus
    revision_notes: str | None = None
    validation: ContentValidationSummary | None = None
    created_at: datetime


class ContentVersionListResponse(BaseModel):
    """Riwayat versi satu konten, terbaru lebih dulu."""

    items: list[ContentVersionSummary]


class ContentSelection(BaseModel):
    """Pilihan konten untuk satu keputusan review.

    Tanpa ``content_ids`` maupun ``week_number`` berarti seluruh konten pada
    workflow tersebut. Keduanya tidak boleh dikirim bersamaan.
    """

    content_ids: list[str] | None = Field(
        default=None,
        description="Daftar content id; versi terbaru tiap id yang diputuskan.",
    )
    week_number: int | None = Field(
        default=None, ge=1, description="Seluruh konten pada satu minggu."
    )


class ContentApproveRequest(ContentSelection):
    """Body ``POST .../contents/approve`` (boleh kosong = seluruh konten)."""


class ContentRejectRequest(ContentSelection):
    """Body ``POST .../contents/reject``; catatan revisi wajib."""

    notes: str = Field(
        default="", description="Catatan revisi untuk dosen; wajib diisi."
    )


class ContentDecisionResponse(BaseModel):
    """Hasil satu keputusan review beserta keadaan konten setelahnya."""

    workflow_id: str
    decision: str
    items: list[ContentSummary]


# --- Contoh response OpenAPI ------------------------------------------------

_WORKFLOW = "wF7cQ2mTb9Xr4nWvHc3sAe"
_PLAN = "cP4dR8kLm2Yt6bQnVx5wZe"
_WEEK = "cW9hJ3pQs7Vb1nMkLx4tYr"
_CREATED = "2026-05-20T09:00:00Z"
_VALIDATION = {
    "status": "PASSED",
    "score": 1.0,
    "retry_count": 0,
    "validated_at": _CREATED,
    "checks": {"schema": "PASSED", "traceability": "PASSED"},
    "errors": None,
    "warnings": None,
    "created_at": _CREATED,
}
_TRACEABILITY = {
    "week_number": 3,
    "sub_cpmk_codes": ["Sub-CPMK-3.1"],
    "weekly_plan_ref": _WEEK,
}


def _example(
    kind: ContentKind,
    *,
    title: str,
    content_data: dict,
    content_markdown: str | None = None,
) -> dict:
    return {
        "id": "Q4x9LbT7pXr2nWvHc3sAeK",
        "content_key": f"{_WORKFLOW}:3:{kind.value}",
        "kind": kind.value,
        "week_number": 3,
        "title": title,
        "version": 1,
        "status": "PENDING_REVIEW",
        "revision_notes": None,
        "workflow_id": _WORKFLOW,
        "course_plan_id": _PLAN,
        "course_plan_week_id": _WEEK,
        "content_data": content_data,
        "content_markdown": content_markdown,
        "prompt_version": f"{kind.value.lower()}/v1",
        "model_name": "gpt-4o-mini",
        "validation": _VALIDATION,
        "created_at": _CREATED,
        "updated_at": _CREATED,
    }


CONTENT_DETAIL_EXAMPLES: dict[str, dict] = {
    "LEARNING_MATERIAL": {
        "summary": "Materi pembelajaran (tabel contents)",
        "value": _example(
            ContentKind.LEARNING_MATERIAL,
            title="Normalisasi Basis Data",
            content_data={
                "learning_objectives": [
                    "Menjelaskan tujuan normalisasi",
                    "Menerapkan 1NF sampai 3NF pada tabel sederhana",
                ],
                "sections": [
                    {
                        "heading": "Pengantar",
                        "body_markdown": "Normalisasi mengurangi **redundansi** data.",
                    }
                ],
                "traceability": _TRACEABILITY,
            },
            content_markdown=(
                "## Tujuan Pembelajaran\n\n- Menjelaskan tujuan normalisasi\n\n"
                "## Pengantar\n\nNormalisasi mengurangi **redundansi** data."
            ),
        ),
    },
    "RESOURCE": {
        "summary": "Referensi pendukung (tabel contents)",
        "value": _example(
            ContentKind.RESOURCE,
            title="Database Normalization Explained",
            content_data={
                "url": "https://example.com/normalization",
                "description": "Penjelasan bertahap 1NF-3NF dengan contoh.",
                "resource_kind": "ARTICLE",
                "relevance_reason": (
                    "Melengkapi materi minggu 3 dengan contoh tambahan."
                ),
                "traceability": _TRACEABILITY,
            },
        ),
    },
    "ASSIGNMENT": {
        "summary": "Tugas (tabel activities)",
        "value": _example(
            ContentKind.ASSIGNMENT,
            title="Normalisasi Studi Kasus Perpustakaan",
            content_data={
                "instructions_markdown": (
                    "Normalkan tabel peminjaman buku hingga **3NF**."
                ),
                "expected_outputs": [
                    "Dokumen PDF berisi tahapan normalisasi",
                    "Diagram ERD akhir",
                ],
                "rubric": [
                    {
                        "criterion": "Ketepatan 1NF-3NF",
                        "description": "Tahapan benar dan lengkap",
                        "weight_percent": 60,
                    },
                    {
                        "criterion": "Kualitas ERD",
                        "description": "Relasi dan kardinalitas tepat",
                        "weight_percent": 40,
                    },
                ],
                "traceability": _TRACEABILITY,
            },
        ),
    },
    "QUIZ": {
        "summary": "Kuis (tabel activities)",
        "value": _example(
            ContentKind.QUIZ,
            title="Kuis Normalisasi",
            content_data={
                "description": "Kuis singkat pemahaman 1NF-3NF.",
                "config": {
                    "time_limit_minutes": 15,
                    "max_attempts": 2,
                    "shuffle_questions": True,
                    "passing_score_percent": 70,
                },
                "questions": [
                    {
                        "question_text": "Tabel disebut memenuhi 1NF jika...",
                        "options": [
                            {"key": "A", "text": "Semua kolom bernilai atomik"},
                            {"key": "B", "text": "Tidak ada primary key"},
                        ],
                        "correct_option_key": "A",
                        "explanation": (
                            "1NF mensyaratkan nilai atomik dan tidak ada grup "
                            "berulang."
                        ),
                    }
                ],
                "traceability": _TRACEABILITY,
            },
        ),
    },
}
