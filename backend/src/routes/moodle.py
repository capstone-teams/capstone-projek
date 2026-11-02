from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response, status

from src.schemas.moodle import (
    ApiErrorResponse,
    CreateMoodleCourseRequest,
    MoodleCourseContentsResponse,
    MoodleCourseListResponse,
    MoodleCourseResponse,
    MoodleSectionResponse,
    MoodleStatusResponse,
    SaveMoodleSectionRequest,
)
from src.services.dependencies import (
    get_moodle_integration_service,
    require_development_environment,
    require_roles,
)
from src.services.moodle_integration_service import MoodleIntegrationService
from src.services.user.enums import UserRole

ERROR_RESPONSES = {
    401: {"model": ApiErrorResponse, "description": "AUTHENTICATION_FAILED"},
    403: {"model": ApiErrorResponse, "description": "AUTHORIZATION_DENIED"},
    404: {"model": ApiErrorResponse, "description": "RESOURCE_NOT_FOUND"},
    422: {
        "model": ApiErrorResponse,
        "description": "Request tidak valid, atau MOODLE_ERROR kategori validation",
    },
    502: {
        "model": ApiErrorResponse,
        "description": "MOODLE_ERROR kategori authentication, permission, transient, atau execution",
    },
    504: {"model": ApiErrorResponse, "description": "MOODLE_ERROR: Moodle tidak merespons tepat waktu"},
}

router = APIRouter(
    prefix="/integrations/moodle",
    tags=["Moodle Integration"],
    responses=ERROR_RESPONSES,
)

instructor_only = require_roles(UserRole.INSTRUCTOR)

MoodleCourseIdPath = Annotated[int, Path(ge=1, description="ID course di Moodle")]
ServiceDependency = Annotated[MoodleIntegrationService, Depends(get_moodle_integration_service)]


@router.get(
    "/status",
    response_model=MoodleStatusResponse,
    summary="Status koneksi Moodle",
    dependencies=[Depends(instructor_only)],
)
async def get_status(service: ServiceDependency) -> MoodleStatusResponse:
    """Status koneksi, versi Moodle, dan ketersediaan external function yang dibutuhkan."""
    return MoodleStatusResponse.model_validate(await service.get_status())


@router.get(
    "/courses",
    response_model=MoodleCourseListResponse,
    summary="Daftar course Moodle",
    dependencies=[Depends(instructor_only)],
)
async def list_courses(service: ServiceDependency) -> MoodleCourseListResponse:
    """Daftar course Moodle yang dapat dipilih dosen sebagai course target."""
    courses = await service.list_courses()
    return MoodleCourseListResponse(
        courses=[MoodleCourseResponse.model_validate(course) for course in courses]
    )


@router.get(
    "/courses/{moodle_course_id}",
    response_model=MoodleCourseResponse,
    summary="Detail course Moodle",
    dependencies=[Depends(instructor_only)],
)
async def get_course(
    moodle_course_id: MoodleCourseIdPath, service: ServiceDependency
) -> MoodleCourseResponse:
    """Informasi satu course; 404 bila course tidak ada di Moodle."""
    return MoodleCourseResponse.model_validate(await service.get_course(moodle_course_id))


@router.get(
    "/courses/{moodle_course_id}/contents",
    response_model=MoodleCourseContentsResponse,
    summary="Section dan module course Moodle",
    dependencies=[Depends(instructor_only)],
)
async def get_course_contents(
    moodle_course_id: MoodleCourseIdPath, service: ServiceDependency
) -> MoodleCourseContentsResponse:
    """Isi course yang sebenarnya ada di Moodle saat ini, termasuk konten module Page."""
    contents = await service.get_course_contents(moodle_course_id)
    return MoodleCourseContentsResponse.model_validate(contents)


@router.post(
    "/courses",
    response_model=MoodleCourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Buat course Moodle untuk pengujian (development saja)",
    dependencies=[Depends(require_development_environment), Depends(instructor_only)],
)
async def create_course(
    payload: CreateMoodleCourseRequest, service: ServiceDependency
) -> MoodleCourseResponse:
    course = await service.create_course(
        fullname=payload.fullname,
        shortname=payload.shortname,
        category_id=payload.category_id,
    )
    return MoodleCourseResponse.model_validate(course)


@router.post(
    "/courses/{moodle_course_id}/sections",
    response_model=MoodleSectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Buat atau perbarui section Moodle untuk pengujian (development saja)",
    responses={200: {"description": "Section yang sudah ada diperbarui"}},
    dependencies=[Depends(require_development_environment), Depends(instructor_only)],
)
async def save_section(
    moodle_course_id: MoodleCourseIdPath,
    payload: SaveMoodleSectionRequest,
    response: Response,
    service: ServiceDependency,
) -> MoodleSectionResponse:
    """Membuat section baru, atau mengubah nama section bila ``section_number`` sudah ada."""
    result = await service.save_section(
        moodle_course_id, name=payload.name, section_number=payload.section_number
    )
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return MoodleSectionResponse.model_validate(result.section)