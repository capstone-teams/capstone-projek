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

import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Response, UploadFile, status

from src.schemas.moodle import (
    AddMoodleParticipantRequest,
    ApiErrorResponse,
    CreateMoodleCourseRequest,
    MoodleParticipantListResponse,
    MoodleParticipantResponse,
    MoodleParticipantRoleResponse,
    MoodleCourseContentsResponse,
    MoodleCourseListResponse,
    MoodleCourseResponse,
    MoodleSectionResponse,
    MoodleStatusResponse,
    SaveMoodleSectionRequest,
    AddCourseSectionRequest,
    RenameCourseSectionRequest,
)
from src.schemas.course_activity import (
    ActivityModname,
    CreateActivityRequest,
    CreateActivityResponse,
    GenerateActivityResponse,
)
from src.services.course_activity_service import (
    ActivityGenerationError,
    CourseActivityService,
    ReferenceFile,
)
from src.services.course_plan.errors import CoursePlanDomainError
from src.services.course_plan.service import CoursePlanService
from src.services.dependencies import (
    get_course_plan_service,
    get_moodle_integration_service,
    get_rps_service,
    get_workflow_service,
    require_development_environment,
    require_roles,
)
from src.services.llm.base import LLMProviderError
from src.services.llm.service import get_llm_service
from src.services.moodle_integration_service import (
    MoodleEnrolment,
    MoodleIntegrationService,
)
from src.services.rps.errors import RPSDomainError
from src.services.rps.service import RPSService
from src.services.workflow.service import WorkflowService
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

# --- Aktivitas dari halaman kursus (Assignment, Quiz, Text and media area) -------------------


async def _activity_references(
    *,
    moodle_course_id: int,
    owner_id: str,
    section: int,
    workflows: WorkflowService,
    plans: CoursePlanService,
    rps: RPSService,
) -> tuple[dict | None, str]:
    """Rencana minggu ``section`` dan ringkasan RPS dari workflow terbaru yang menargetkan kursus ini."""
    candidates = [
        workflow
        for workflow in await workflows.list_workflows(owner_id=owner_id)
        if workflow.moodle_course_id == moodle_course_id
    ]
    if not candidates:
        return None, ""
    workflow = max(candidates, key=lambda item: item.updated_at or item.created_at)
    plan_week: dict | None = None
    try:
        plan = await plans.get_latest(workflow_id=workflow.id or "", owner_id=owner_id)
    except CoursePlanDomainError:
        plan = None
    if plan is not None:
        week = next((item for item in plan.weeks if item.week_number == section), None)
        if week is not None:
            plan_week = {
                "minggu": week.week_number,
                "judul": week.title,
                "jenis_minggu": week.week_type,
                "capaian": list(week.learning_outcomes),
                "tujuan": list(week.objectives),
                "topik": list(week.topics),
                "metode": list(week.teaching_methods),
                "rencana_aktivitas": list(week.planned_activities),
            }
    rps_text = ""
    if workflow.rps_id:
        try:
            document = await rps.get_rps(rps_id=workflow.rps_id, owner_id=owner_id)
            if document.structured_data:
                rps_text = json.dumps(document.structured_data, ensure_ascii=False)
        except RPSDomainError:
            rps_text = ""
    return plan_week, rps_text


def _activity_service(
    moodle: MoodleIntegrationService,
    workflows: WorkflowService,
    plans: CoursePlanService,
    rps: RPSService,
    *,
    with_llm: bool,
) -> CourseActivityService:
    async def references(moodle_course_id: int, owner_id: str, section: int):
        return await _activity_references(
            moodle_course_id=moodle_course_id,
            owner_id=owner_id,
            section=section,
            workflows=workflows,
            plans=plans,
            rps=rps,
        )

    llm = None
    if with_llm:
        try:
            llm = get_llm_service()
        except LLMProviderError:
            llm = None
    return CourseActivityService(moodle, llm=llm, references=references)


@router.post(
    "/courses/{moodle_course_id}/activities",
    response_model=CreateActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tambah Assignment, Quiz, atau Text and media area pada satu section",
    dependencies=[Depends(instructor_only)],
)
async def create_activity(
    moodle_course_id: MoodleCourseIdPath,
    payload: CreateActivityRequest,
    service: ServiceDependency,
) -> CreateActivityResponse:
    """Membuat activity lewat plugin ``local_capstonebridge`` (``create_assign``/``create_quiz``/``create_label``)."""
    return await CourseActivityService(service).create(moodle_course_id, payload)


@router.post(
    "/courses/{moodle_course_id}/activities/generate",
    response_model=GenerateActivityResponse,
    summary="Draf isi activity dengan AI dari materi minggu, RPS, dan file referensi",
)
async def generate_activity(
    moodle_course_id: MoodleCourseIdPath,
    service: ServiceDependency,
    modname: Annotated[ActivityModname, Form()],
    section: Annotated[int, Form(ge=0)],
    instruction: Annotated[str, Form(max_length=2000)] = "",
    question_count: Annotated[int, Form(ge=1, le=30)] = 10,
    difficulty: Annotated[str, Form(max_length=20)] = "sedang",
    use_week: Annotated[bool, Form()] = True,
    use_rps: Annotated[bool, Form()] = True,
    reference_file: UploadFile | None = File(default=None),
    current_user: User = Depends(instructor_only),
    workflows: WorkflowService = Depends(get_workflow_service),
    plans: CoursePlanService = Depends(get_course_plan_service),
    rps: RPSService = Depends(get_rps_service),
) -> GenerateActivityResponse:
    """Draf hanya mengisi formulir; activity dibuat setelah dosen menyimpannya lewat ``POST .../activities``."""
    activities = _activity_service(service, workflows, plans, rps, with_llm=True)
    file = None
    if reference_file is not None and reference_file.filename:
        file = ReferenceFile(filename=reference_file.filename, content=await reference_file.read())
    try:
        return await activities.generate(
            moodle_course_id,
            owner_id=current_user.id,
            modname=modname,
            section=section,
            instruction=instruction,
            question_count=question_count,
            difficulty=difficulty,
            use_week=use_week,
            use_rps=use_rps,
            reference_file=file,
        )
    except ActivityGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.public_message) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.public_message) from exc



# --- Section dari Edit mode halaman course (dosen) ------------------------------------------


@router.post(
    "/courses/{moodle_course_id}/course-sections",
    response_model=MoodleSectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tambah section di akhir course",
    dependencies=[Depends(instructor_only)],
)
async def add_course_section(
    moodle_course_id: MoodleCourseIdPath,
    service: ServiceDependency,
    payload: AddCourseSectionRequest | None = None,
) -> MoodleSectionResponse:
    """Section baru setelah section terakhir, memakai token integrasi backend (bukan sesi Moodle di browser)."""
    name = payload.name if payload is not None else ""
    if not name:
        contents = await service.get_course_contents(moodle_course_id)
        next_number = max((section.section_number for section in contents.sections), default=0) + 1
        name = f"Pertemuan {next_number}"
    result = await service.save_section(moodle_course_id, name=name)
    return MoodleSectionResponse.model_validate(result.section)


@router.put(
    "/courses/{moodle_course_id}/course-sections/{section_id}",
    response_model=MoodleSectionResponse,
    summary="Ganti nama section",
    dependencies=[Depends(instructor_only)],
)
async def rename_course_section(
    moodle_course_id: MoodleCourseIdPath,
    section_id: Annotated[int, Path(ge=1, description="ID section di Moodle")],
    payload: RenameCourseSectionRequest,
    service: ServiceDependency,
) -> MoodleSectionResponse:
    """Nama section diubah lewat ``core_update_inplace_editable`` dengan token integrasi backend."""
    contents = await service.get_course_contents(moodle_course_id)
    if not any(section.moodle_section_id == section_id for section in contents.sections):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section tidak ditemukan pada course ini.")
    result = await service.save_section(moodle_course_id, name=payload.name, section_id=section_id)
    return MoodleSectionResponse.model_validate(result.section)


# --- Peserta course (BE-04.5) ------------------------------------------------

#: Role permintaan → shortname Moodle yang dipakai UI (``teacher`` = role 3/editingteacher).
_PARTICIPANT_ROLE_SHORTNAMES = {"teacher": "editingteacher", "student": "student"}


def _participant_response(enrolment: MoodleEnrolment) -> MoodleParticipantResponse:
    return MoodleParticipantResponse(
        id=enrolment.user.moodle_user_id,
        username=enrolment.user.username,
        fullname=enrolment.user.fullname,
        email=enrolment.user.email,
        roles=[
            MoodleParticipantRoleResponse(shortname=shortname, name=shortname)
            for shortname in enrolment.roles
        ],
    )


@router.get(
    "/courses/{moodle_course_id}/participants",
    response_model=MoodleParticipantListResponse,
    summary="Peserta course Moodle",
    dependencies=[Depends(instructor_only)],
)
async def list_participants(
    moodle_course_id: MoodleCourseIdPath, service: ServiceDependency
) -> MoodleParticipantListResponse:
    """Peserta yang benar-benar terdaftar di Moodle, dibaca dengan token integrasi backend."""
    enrolments = await service.get_enrolled_users(moodle_course_id)
    return MoodleParticipantListResponse(
        participants=[_participant_response(enrolment) for enrolment in enrolments]
    )


@router.post(
    "/courses/{moodle_course_id}/participants",
    response_model=MoodleParticipantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tambahkan peserta dari akun Moodle",
    dependencies=[Depends(instructor_only)],
)
async def add_participant(
    moodle_course_id: MoodleCourseIdPath,
    payload: AddMoodleParticipantRequest,
    service: ServiceDependency,
) -> MoodleParticipantResponse:
    """Daftarkan akun Moodle yang sudah ada ke course lewat ``enrol_manual_enrol_users``.

    Pencarian memakai email atau username persis karena itulah yang diketahui
    dosen. Enrolment manual idempoten: akun yang sudah terdaftar tidak menjadi
    anggota ganda.
    """
    user = await service.find_user(payload.query)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Akun Moodle dengan email atau username tersebut tidak ditemukan. "
                "Pastikan akun sudah dibuat di Moodle."
            ),
        )
    await service.enrol_users(moodle_course_id, [(user.moodle_user_id, payload.role)])
    return _participant_response(
        MoodleEnrolment(
            user=user, roles=(_PARTICIPANT_ROLE_SHORTNAMES[payload.role],)
        )
    )
