"""Endpoint baca course, course plan, dan konten mingguan.

Router ini hanya urusan HTTP: kontrak, dependency, dan pemetaan entity → DTO.
Query berada di :mod:`src.services.course`.

Cakupan sengaja **read-only**. Endpoint tulis (generate plan/konten, approve,
regenerate) adalah bagian generator (BE-14) dan belum ada; tanpa endpoint baca,
data yang sudah ada di database — termasuk hasil ``scripts/seed_sample_course.py``
— tidak dapat diperiksa frontend maupun QA.

Kontrak mengikuti ``docs/02. design/design-api.md`` §8–§10 dan bentuk respons
yang sudah dipakai frontend (``frontend/src/services/courseService.js``).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from src.schemas.course import (
    ActivityItem,
    ContentItem,
    CourseContentResponse,
    CourseDetailResponse,
    CourseListResponse,
    CoursePlanResponse,
    CourseSummary,
    PlanWeekItem,
    WeekContentItem,
)
from src.schemas.errors import ErrorResponse
from src.services.course import CourseReadService
from src.services.dependencies import get_course_service, require_roles
from src.services.user.domain import User
from src.services.user.enums import UserRole

router = APIRouter(prefix="/courses", tags=["Courses"])

# Policy instructor-only, sama seperti endpoint RPS dan setup dosen (design-api §22).
instructor_only = require_roles(UserRole.INSTRUCTOR)

NOT_FOUND_RESPONSE = {
    "model": ErrorResponse,
    "description": (
        "Course tidak ada atau bukan milik dosen yang login — keduanya respons "
        "yang sama agar keberadaan course dosen lain tidak dapat ditebak."
    ),
}
AUTHORIZATION_RESPONSE = {
    "model": ErrorResponse,
    "description": "Role bukan `INSTRUCTOR`; response tidak menyebut role yang dibutuhkan.",
}
AUTHENTICATION_RESPONSE = {
    "model": ErrorResponse,
    "description": "Token tidak ada, kedaluwarsa, atau tidak valid.",
}

COMMON_RESPONSES = {
    401: AUTHENTICATION_RESPONSE,
    403: AUTHORIZATION_RESPONSE,
    404: NOT_FOUND_RESPONSE,
}


def _list(value: Any) -> list[Any]:
    """JSONB list dari database boleh ``None``; DTO selalu list."""
    return list(value) if isinstance(value, list) else []


def _course_summary(course) -> CourseSummary:
    return CourseSummary(
        id=course.id,
        shortname=course.shortname,
        fullname=course.fullname,
        status=course.status.value,
        semester=course.semester,
        moodle_course_id=course.moodle_course_id,
    )


def _course_detail(course) -> CourseDetailResponse:
    return CourseDetailResponse(
        **_course_summary(course).model_dump(),
        instructor_id=course.instructor_id,
        rps_id=course.rps_id,
        description=course.description,
        created_at=course.created_at,
        updated_at=course.updated_at,
    )


def _plan_week(week) -> PlanWeekItem:
    return PlanWeekItem(
        week_number=week.week_number,
        title=week.title,
        learning_outcomes=[str(item) for item in _list(week.learning_outcomes)],
        topics=[str(item) for item in _list(week.topics)],
        teaching_methods=[str(item) for item in _list(week.methods)],
        assessment=week.assessment,
    )


def _content_item(content) -> ContentItem:
    """Ratakan ``content_data`` ke field DTO (lihat catatan di modul schema)."""
    data = content.content_data if isinstance(content.content_data, dict) else {}
    return ContentItem(
        content_id=content.id,
        type=content.content_type.value.lower(),
        title=content.title,
        version=content.version,
        status=content.status.value,
        summary=data.get("summary"),
        sections=_list(data.get("sections")),
        examples=_list(data.get("examples")),
        references=_list(data.get("references")),
        description=data.get("description"),
        resource_type=data.get("resource_type"),
        url=data.get("url"),
        body_markdown=content.content_markdown,
    )


def _activity_item(activity) -> ActivityItem:
    return ActivityItem(
        activity_id=activity.id,
        type=activity.type.value.lower(),
        title=activity.title,
        version=activity.version,
        status=activity.status.value,
        data=activity.activity_data,
    )


def _week_items(weeks, contents, activities) -> list[WeekContentItem]:
    """Susun minggu + kontennya; hanya versi terbaru per jenis yang dipakai.

    ``list_contents``/``list_activities`` mengurutkan versi tertinggi lebih dulu,
    sehingga entri pertama untuk sebuah ``(minggu, jenis)`` adalah versi terbaru.
    """
    by_week: dict[str, dict[str, ContentItem]] = {}
    for content in contents:
        slot = by_week.setdefault(content.course_plan_week_id, {})
        slot.setdefault(content.content_type.value.lower(), _content_item(content))

    activities_by_week: dict[str, dict[str, ActivityItem]] = {}
    for activity in activities:
        slot = activities_by_week.setdefault(activity.course_plan_week_id, {})
        slot.setdefault(activity.type.value.lower(), _activity_item(activity))

    items: list[WeekContentItem] = []
    for week in weeks:
        content_slot = by_week.get(week.id, {})
        activity_slot = activities_by_week.get(week.id, {})
        items.append(
            WeekContentItem(
                week=week.week_number,
                topic=week.title,
                learning_objectives=[str(item) for item in _list(week.learning_outcomes)],
                materials=[item for key, item in content_slot.items() if key == "learning_material"],
                resources=[item for key, item in content_slot.items() if key == "resource"],
                activities={
                    "assignment": activity_slot.get("assignment"),
                    "quiz": activity_slot.get("quiz"),
                },
            )
        )
    return items


@router.get("", response_model=CourseListResponse, responses=COMMON_RESPONSES)
async def list_courses(
    current_user: User = Depends(instructor_only),
    service: CourseReadService = Depends(get_course_service),
) -> CourseListResponse:
    """Course milik dosen yang login (design-api §8)."""
    courses = await service.list_courses(instructor_id=current_user.id)
    return CourseListResponse(items=[_course_summary(course) for course in courses])


@router.get("/{course_id}", response_model=CourseDetailResponse, responses=COMMON_RESPONSES)
async def read_course(
    course_id: str,
    current_user: User = Depends(instructor_only),
    service: CourseReadService = Depends(get_course_service),
) -> CourseDetailResponse:
    """Detail satu course milik dosen yang login."""
    course = await service.get_course(course_id=course_id, instructor_id=current_user.id)
    return _course_detail(course)


@router.get(
    "/{course_id}/plan", response_model=CoursePlanResponse, responses=COMMON_RESPONSES
)
async def read_course_plan(
    course_id: str,
    current_user: User = Depends(instructor_only),
    service: CourseReadService = Depends(get_course_service),
) -> CoursePlanResponse:
    """Rencana pembelajaran terbaru beserta minggunya.

    Course yang belum punya rencana tetap ``200`` dengan ``plan_id: null`` dan
    ``weeks: []`` — frontend dapat menampilkan empty state tanpa membedakan 404.
    """
    course = await service.get_course(course_id=course_id, instructor_id=current_user.id)
    plan = await service.get_plan(course_id=course.id)
    if plan is None:
        return CoursePlanResponse(course_id=course.id)
    weeks = await service.list_weeks(plan_id=plan.id)
    return CoursePlanResponse(
        course_id=course.id,
        plan_id=plan.id,
        version=plan.version,
        status=plan.status.value,
        weeks=[_plan_week(week) for week in weeks],
    )


@router.get(
    "/{course_id}/content", response_model=CourseContentResponse, responses=COMMON_RESPONSES
)
async def read_course_content(
    course_id: str,
    week: Annotated[int | None, Query(ge=1, description="Filter satu minggu.")] = None,
    current_user: User = Depends(instructor_only),
    service: CourseReadService = Depends(get_course_service),
) -> CourseContentResponse:
    """Konten mingguan hasil generate (design-api §10.3).

    ``?week=N`` memfilter satu minggu. Minggu tanpa konten tetap muncul dengan
    ``materials``/``resources`` kosong dan ``activities`` ``null`` — lebih berguna
    daripada menghilangkannya, karena UI perlu menandai minggu yang belum
    digenerate.
    """
    course = await service.get_course(course_id=course_id, instructor_id=current_user.id)
    plan = await service.get_plan(course_id=course.id)
    if plan is None:
        return CourseContentResponse(course_id=course.id)

    weeks = await service.list_weeks(plan_id=plan.id)
    if week is not None:
        weeks = [item for item in weeks if item.week_number == week]

    week_ids = [item.id for item in weeks]
    contents = await service.list_contents(week_ids=week_ids)
    activities = await service.list_activities(week_ids=week_ids)
    return CourseContentResponse(
        course_id=course.id, weeks=_week_items(weeks, contents, activities)
    )
