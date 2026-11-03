"""Modul course plan (BE-14).

- ``domain`` — record versi rencana dan aturan nilainya;
- ``repository`` — akses tabel ``course_plans``/``course_plan_weeks``;
- ``service`` — operasi versi rencana (simpan, baca, review);
- ``errors`` — error domain beserta kontrak HTTP-nya.
"""

from src.services.course_plan.domain import (
    CoursePlanDraft,
    CoursePlanRecord,
    CoursePlanWeekRecord,
    validation_passed,
)
from src.services.course_plan.errors import (
    CoursePlanDomainError,
    CoursePlanGenerationError,
    CoursePlanNotFoundError,
    CoursePlanStateError,
    CoursePlanValidationError,
)
from src.services.course_plan.repository import CoursePlanRepository
from src.services.course_plan.service import CoursePlanService

__all__ = [
    "CoursePlanDomainError",
    "CoursePlanDraft",
    "CoursePlanGenerationError",
    "CoursePlanNotFoundError",
    "CoursePlanRecord",
    "CoursePlanRepository",
    "CoursePlanService",
    "CoursePlanStateError",
    "CoursePlanValidationError",
    "CoursePlanWeekRecord",
    "validation_passed",
]
