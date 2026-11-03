"""Representasi domain course plan (BE-14.1).

Dataclass di sini adalah domain model, bukan entity persistence: bentuk yang
dibaca/ditulis service dan route, tanpa SQLAlchemy. Entity tabelnya tetap
``src.models.course_plan`` dan ``src.models.course_plan_week`` yang diakses
:class:`~src.services.course_plan.repository.CoursePlanRepository`.

Satu :class:`CoursePlanRecord` mewakili **satu versi**; daftar versi adalah
beberapa record. Versi lama tidak pernah diubah saat regenerasi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.models.course_plan import CoursePlanStatus

__all__ = [
    "CoursePlanDraft",
    "CoursePlanRecord",
    "CoursePlanWeekRecord",
    "validation_passed",
]


def validation_passed(result: dict | None) -> bool:
    """``True`` hanya bila validasi tersimpan menyatakan lolos.

    ``None`` (belum pernah divalidasi, mis. baris lama) dianggap **belum lolos**
    sehingga approve tidak dapat melewati validasi yang belum dijalankan.
    """
    return bool(result and result.get("passed") is True)


@dataclass(frozen=True, kw_only=True)
class CoursePlanWeekRecord:
    """Satu minggu pada sebuah versi course plan."""

    week_number: int
    title: str
    learning_outcomes: tuple[str, ...] = ()
    objectives: tuple[str, ...] = ()
    topics: tuple[str, ...] = ()
    teaching_methods: tuple[str, ...] = ()
    planned_activities: tuple[str, ...] = ()
    week_type: str = "regular"
    rps_week: int | None = None
    id: str | None = None


@dataclass(frozen=True, kw_only=True)
class CoursePlanRecord:
    """Satu versi course plan beserta minggu-minggunya."""

    id: str
    workflow_id: str | None
    rps_id: str | None
    version: int
    status: CoursePlanStatus
    course: dict = field(default_factory=dict)
    weeks: tuple[CoursePlanWeekRecord, ...] = ()
    weeks_count: int = 0
    validation_result: dict | None = None
    activity_configuration: dict | None = None
    revision_notes: str | None = None
    regeneration_instruction: str | None = None
    prompt_version: str | None = None
    model_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    approved_at: datetime | None = None

    @property
    def validation_passed(self) -> bool:
        return validation_passed(self.validation_result)


@dataclass(frozen=True, kw_only=True)
class CoursePlanDraft:
    """Versi baru yang siap disimpan (belum punya id/waktu database)."""

    workflow_id: str
    rps_id: str
    course: dict
    weeks: tuple[CoursePlanWeekRecord, ...]
    plan_data: dict
    version: int = 1
    course_id: str | None = None
    rps_analysis_id: str | None = None
    activity_configuration: dict | None = None
    validation_result: dict | None = None
    revision_notes: str | None = None
    regeneration_instruction: str | None = None
    prompt_version: str | None = None
    model_name: str | None = None
