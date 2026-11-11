"""Endpoint Moodle Integration Layer (BE-04.7) dan akses course untuk mahasiswa.

Endpoint baca course (``GET /courses``, ``/courses/{id}``, ``/courses/{id}/contents``)
dipakai frontend sebagai gateway untuk kedua role:

- dosen melihat seluruh course Moodle (untuk memilih course target) beserta
  isinya apa adanya, termasuk yang tersembunyi;
- mahasiswa hanya melihat course terlihat tempat ia terdaftar, tanpa section dan
  activity yang disembunyikan (:mod:`src.services.moodle_student_courses`).
  Course lain menghasilkan 404 yang sama seperti tidak ada.

Status koneksi dan endpoint write tetap khusus dosen.
"""

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
from src.services.moodle_student_courses import StudentCourseService
from src.services.user.domain import User
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
#: Pembaca course: dosen (seluruh course) dan mahasiswa (course tempat ia terdaftar).
course_reader = require_roles(UserRole.INSTRUCTOR, UserRole.STUDENT)
#: Section OpenAPI untuk endpoint yang juga dipakai mahasiswa (halaman course mahasiswa).
STUDENT_ACCESS_TAG = "Student Access"

MoodleCourseIdPath = Annotated[int, Path(ge=1, description="ID course di Moodle")]
ServiceDependency = Annotated[MoodleIntegrationService, Depends(get_moodle_integration_service)]
ReaderDependency = Annotated[User, Depends(course_reader)]


def _student_view(user: User, service: MoodleIntegrationService) -> StudentCourseService | None:
    """Service pembatas untuk mahasiswa; ``None`` untuk dosen."""
    return StudentCourseService(service) if user.role is UserRole.STUDENT else None


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
    tags=[STUDENT_ACCESS_TAG],
)
async def list_courses(
    user: ReaderDependency, service: ServiceDependency
) -> MoodleCourseListResponse:
    """Dosen: course yang dapat dipilih sebagai course target. Mahasiswa: course tempat ia terdaftar."""
    student = _student_view(user, service)
    courses = (
        await student.list_courses(user.username)
        if student is not None
        else await service.list_courses()
    )
    return MoodleCourseListResponse(
        courses=[MoodleCourseResponse.model_validate(course) for course in courses]
    )


@router.get(
    "/courses/{moodle_course_id}",
    response_model=MoodleCourseResponse,
    summary="Detail course Moodle",
    tags=[STUDENT_ACCESS_TAG],
)
async def get_course(
    moodle_course_id: MoodleCourseIdPath,
    user: ReaderDependency,
    service: ServiceDependency,
) -> MoodleCourseResponse:
    """Informasi satu course; 404 bila course tidak ada (atau, bagi mahasiswa, tidak dapat diakses)."""
    student = _student_view(user, service)
    course = (
        await student.get_course(user.username, moodle_course_id)
        if student is not None
        else await service.get_course(moodle_course_id)
    )
    return MoodleCourseResponse.model_validate(course)


@router.get(
    "/courses/{moodle_course_id}/contents",
    response_model=MoodleCourseContentsResponse,
    summary="Section dan module course Moodle",
    tags=[STUDENT_ACCESS_TAG],
)
async def get_course_contents(
    moodle_course_id: MoodleCourseIdPath,
    user: ReaderDependency,
    service: ServiceDependency,
) -> MoodleCourseContentsResponse:
    """Isi course yang sebenarnya ada di Moodle saat ini.

    Memuat isi module Page, alamat module URL, dan intro assignment/quiz. Bagi
    mahasiswa hanya section dan activity yang terlihat yang dikirim.
    """
    student = _student_view(user, service)
    contents = (
        await student.get_course_contents(user.username, moodle_course_id)
        if student is not None
        else await service.get_course_contents(moodle_course_id, with_intros=True)
    )
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