"""Domain konten hasil generation (BE-19.1).

Satu :class:`ContentRecord` adalah satu **versi** konten. Identitas konten yang
sama antarversi diwakili ``content_key``; nomor versi naik setiap regenerasi.

Jenis konten mengikuti Content Output Schema (BE-20.1). ``LEARNING_MATERIAL``
dan ``RESOURCE`` disimpan pada tabel ``contents``, sedangkan ``ASSIGNMENT`` dan
``QUIZ`` pada tabel ``activities`` — pemetaan yang sama dengan
``src.schemas.content.REGISTRY``.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime

from src.models.validation_result import ValidationStatus

__all__ = [
    "ApprovalStatus",
    "ContentDraft",
    "ContentKind",
    "ContentRecord",
    "ValidationRecord",
    "content_key_for",
]


class ContentKind(str, enum.Enum):
    """Jenis konten yang dapat dihasilkan (BE-20.1)."""

    LEARNING_MATERIAL = "LEARNING_MATERIAL"
    RESOURCE = "RESOURCE"
    ASSIGNMENT = "ASSIGNMENT"
    QUIZ = "QUIZ"

    @property
    def is_activity(self) -> bool:
        """Apakah jenis ini disimpan pada tabel ``activities``."""
        return self in (ContentKind.ASSIGNMENT, ContentKind.QUIZ)

    @property
    def table(self) -> str:
        return "activities" if self.is_activity else "contents"


class ApprovalStatus(str, enum.Enum):
    """Status approval satu versi konten.

    Nilainya sama dengan ``ContentStatus`` dan ``ActivityStatus`` di model,
    sehingga satu domain dipakai untuk kedua tabel.
    """

    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"


@dataclass(frozen=True)
class ValidationRecord:
    """Satu hasil validasi konten (baris ``validation_results``)."""

    id: str
    status: ValidationStatus
    checks: dict | None
    errors: dict | None
    warnings: dict | None
    score: float | None
    retry_count: int
    validated_at: datetime | None
    created_at: datetime


@dataclass(frozen=True)
class ContentRecord:
    """Satu versi konten beserta hasil validasi terbarunya."""

    id: str
    content_key: str
    kind: ContentKind
    workflow_id: str | None
    course_plan_id: str | None
    course_plan_week_id: str
    week_number: int | None
    title: str
    content_data: dict | None
    content_markdown: str | None
    version: int
    status: ApprovalStatus
    revision_notes: str | None
    prompt_version: str | None
    model_name: str | None
    created_at: datetime
    updated_at: datetime
    validation: ValidationRecord | None = None


@dataclass(frozen=True)
class ContentDraft:
    """Data satu versi konten yang akan disimpan.

    ``content_key`` kosong berarti ini versi pertama dari konten baru; kunci
    dibentuk dari workflow, minggu, dan jenis konten. Regenerasi mengirim
    ``content_key`` versi sebelumnya supaya versi baru menempel pada identitas
    yang sama.
    """

    kind: ContentKind
    workflow_id: str
    course_plan_id: str
    course_plan_week_id: str
    week_number: int
    title: str
    content_data: dict
    content_markdown: str | None = None
    content_key: str | None = None
    status: ApprovalStatus = ApprovalStatus.DRAFT
    revision_notes: str | None = None
    prompt_version: str | None = None
    model_name: str | None = None
    agent_run_id: str | None = None


def content_key_for(workflow_id: str, week_number: int, kind: ContentKind) -> str:
    """Kunci konten deterministik untuk satu jenis konten per minggu.

    Format ``{workflow}:{minggu}:{jenis}`` membuat regenerasi dan eksekusi
    Moodle dapat menemukan konten yang sama tanpa tabel pemetaan tambahan.

    ponytail: satu konten per jenis per minggu, sesuai jumlah yang dihasilkan
    BE-20. Jika nanti satu jenis boleh muncul lebih dari sekali dalam seminggu,
    tambahkan ordinal pada kunci dan migrasikan baris lama.
    """
    return f"{workflow_id}:{week_number}:{kind.value}"
