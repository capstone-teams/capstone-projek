"""DTO endpoint baca course, course plan, dan konten mingguan (design-api §8–§10).

Bentuk respons mengikuti apa yang sudah dipakai frontend
(``frontend/src/services/courseService.js``) dan ``docs/02. design/design-api.md``
§10.3, selama endpoint generator (BE-14) belum ada. DTO di sini hanya untuk
**membaca**; tidak ada request body maupun operasi tulis.

Field ``data`` pada material/resource sengaja tidak dipakai: isi
``contents.content_data`` sudah diratakan ke field eksplisit (``summary``,
``sections``, ``url``, ...) supaya kontrak API stabil dan tidak bergantung pada
JSONB yang belum punya validator.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ActivityItem",
    "ContentItem",
    "CourseContentResponse",
    "CourseDetailResponse",
    "CourseListResponse",
    "CoursePlanResponse",
    "CourseSummary",
    "PlanWeekItem",
    "WeekContentItem",
]


class CourseSummary(BaseModel):
    """Satu course pada ``GET /api/v1/courses``."""

    id: str
    shortname: str
    fullname: str
    status: str
    semester: str | None = None
    moodle_course_id: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "5AH7inFLxJDRKEa34saR9c",
                "shortname": "IF2230-SAMPLE",
                "fullname": "Basis Data (Contoh)",
                "status": "DRAFT",
                "semester": "3",
                "moodle_course_id": None,
            }
        }
    )


class CourseListResponse(BaseModel):
    """Response ``GET /api/v1/courses``."""

    items: list[CourseSummary] = Field(default_factory=list)


class CourseDetailResponse(CourseSummary):
    """Response ``GET /api/v1/courses/{course_id}``."""

    instructor_id: str
    rps_id: str
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PlanWeekItem(BaseModel):
    """Satu minggu pada course plan."""

    week_number: int
    title: str
    learning_outcomes: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    teaching_methods: list[str] = Field(default_factory=list)
    assessment: dict[str, Any] | None = None


class CoursePlanResponse(BaseModel):
    """Response ``GET /api/v1/courses/{course_id}/plan``.

    ``plan`` bernilai ``null`` bila course belum punya rencana; ``weeks`` kosong
    pada kondisi yang sama. Bentuknya tetap sama agar frontend tidak perlu
    menangani dua kontrak.
    """

    course_id: str
    plan_id: str | None = None
    version: int | None = None
    status: str | None = None
    weeks: list[PlanWeekItem] = Field(default_factory=list)


class ContentItem(BaseModel):
    """Satu baris ``contents`` yang sudah diratakan untuk dibaca.

    ``type`` adalah ``learning_material`` atau ``resource``; field yang tidak
    relevan dibiarkan ``null``/kosong.
    """

    content_id: str
    type: str
    title: str
    version: int
    status: str
    summary: str | None = None
    sections: list[dict[str, Any]] = Field(default_factory=list)
    examples: list[dict[str, Any]] = Field(default_factory=list)
    references: list[dict[str, Any]] = Field(default_factory=list)
    description: str | None = None
    resource_type: str | None = None
    url: str | None = None
    body_markdown: str | None = None


class ActivityItem(BaseModel):
    """Satu baris ``activities`` (assignment atau quiz)."""

    activity_id: str
    type: str
    title: str
    version: int
    status: str
    data: dict[str, Any] | None = None


class WeekContentItem(BaseModel):
    """Konten satu minggu."""

    week: int
    topic: str
    learning_objectives: list[str] = Field(default_factory=list)
    materials: list[ContentItem] = Field(default_factory=list)
    resources: list[ContentItem] = Field(default_factory=list)
    activities: dict[str, ActivityItem | None] = Field(
        default_factory=lambda: {"assignment": None, "quiz": None}
    )


class CourseContentResponse(BaseModel):
    """Response ``GET /api/v1/courses/{course_id}/content`` (design-api §10.3)."""

    course_id: str
    weeks: list[WeekContentItem] = Field(default_factory=list)
