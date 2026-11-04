"""Endpoint course plan: baca versi dan review (BE-14.2).

Router ini hanya menangani urusan HTTP: kontrak endpoint, dependency, dan
pemetaan domain → DTO. Keputusan approval, penomoran versi, dan penulisan
``WorkflowEvent`` berada di :mod:`src.services.course_plan`.

Endpoint berbasis workflow (DL-011), bukan course:

| Method | Path                                                | Keterangan                    |
| ------ | --------------------------------------------------- | ----------------------------- |
| GET    | ``/workflows/{workflow_id}/plan``                   | versi terbaru + weekly plan   |
| GET    | ``/workflows/{workflow_id}/plan/versions``          | riwayat versi                 |
| GET    | ``/workflows/{workflow_id}/plan/versions/{version}`` | detail satu versi             |
| POST   | ``/workflows/{workflow_id}/plan/approve``           | setujui versi terbaru         |
| POST   | ``/workflows/{workflow_id}/plan/reject``            | tolak dengan catatan revisi   |

Seluruh endpoint instructor-only dan dibatasi workflow milik dosen yang login
(design-api §22; workflow dosen lain menghasilkan 404 yang sama seperti workflow
tidak ada). Mahasiswa selalu 403.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Path

from src.schemas.course_plan import (
    CoursePlanIdentity,
    CoursePlanResponse,
    CoursePlanValidationResult,
    CoursePlanVersionListResponse,
    CoursePlanVersionSummary,
    PlanGenerationResponse,
    PlanRegenerateRequest,
    PlanRejectRequest,
    PlanWeekResponse,
)
from src.services.course_plan import (
    CoursePlanRecord,
    CoursePlanService,
    CoursePlanWeekRecord,
)
from src.services.dependencies import (
    CoursePlanningRunner,
    get_course_plan_service,
    get_course_planning_runner,
    require_roles,
)
from src.services.user.domain import User
from src.services.user.enums import UserRole
from src.services.user.validation import ID_LENGTH, SHORTUUID_PATTERN

router = APIRouter(tags=["Course Plans"])

#: Pesan response 202 generate/regenerate; pekerjaan berjalan di background.
GENERATION_MESSAGE = (
    "Course planning dijadwalkan; pantau status workflow dan event untuk hasilnya."
)

#: Course plan hanya dapat dibaca/direview dosen (design-api §22).
instructor_only = require_roles(UserRole.INSTRUCTOR)

WorkflowIdPath = Annotated[
    str,
    Path(min_length=ID_LENGTH, max_length=ID_LENGTH, pattern=SHORTUUID_PATTERN),
]

PlanVersionPath = Annotated[
    int,
    Path(ge=1, description="Nomor versi course plan."),
]


def _to_week(week: CoursePlanWeekRecord) -> PlanWeekResponse:
    """Petakan record minggu domain ke DTO."""
    return PlanWeekResponse(
        week_number=week.week_number,
        title=week.title,
        learning_outcomes=list(week.learning_outcomes),
        objectives=list(week.objectives),
        topics=list(week.topics),
        teaching_methods=list(week.teaching_methods),
        planned_activities=list(week.planned_activities),
        week_type=week.week_type,
        rps_week=week.rps_week,
    )


def _to_plan(record: CoursePlanRecord) -> CoursePlanResponse:
    """Petakan satu versi course plan ke response detail."""
    return CoursePlanResponse(
        id=record.id,
        workflow_id=record.workflow_id,
        version=record.version,
        status=record.status.value,
        course=CoursePlanIdentity.model_validate(record.course or {}),
        weeks=[_to_week(week) for week in record.weeks],
        validation=CoursePlanValidationResult.model_validate(
            record.validation_result or {"passed": False, "issues": []}
        ),
        revision_notes=record.revision_notes,
        regeneration_instruction=record.regeneration_instruction,
        prompt_version=record.prompt_version,
        model_name=record.model_name,
        created_at=record.created_at,
        approved_at=record.approved_at,
    )


def _to_summary(record: CoursePlanRecord) -> CoursePlanVersionSummary:
    """Petakan satu versi ke baris riwayat versi."""
    return CoursePlanVersionSummary(
        version=record.version,
        status=record.status.value,
        validation_passed=record.validation_passed,
        revision_notes=record.revision_notes,
        created_at=record.created_at,
        approved_at=record.approved_at,
    )


@router.get(
    "/workflows/{workflow_id}/plan",
    response_model=CoursePlanResponse,
)
async def read_course_plan(
    workflow_id: WorkflowIdPath,
    current_user: User = Depends(instructor_only),
    service: CoursePlanService = Depends(get_course_plan_service),
) -> CoursePlanResponse:
    """Versi terbaru course plan beserta weekly plan dan hasil validasi.

    ``404 RESOURCE_NOT_FOUND`` bila workflow tidak ada, bukan milik dosen yang
    login, atau belum memiliki course plan.
    """
    record = await service.get_latest(
        workflow_id=workflow_id, owner_id=current_user.id
    )
    return _to_plan(record)


@router.get(
    "/workflows/{workflow_id}/plan/versions",
    response_model=CoursePlanVersionListResponse,
)
async def list_course_plan_versions(
    workflow_id: WorkflowIdPath,
    current_user: User = Depends(instructor_only),
    service: CoursePlanService = Depends(get_course_plan_service),
) -> CoursePlanVersionListResponse:
    """Riwayat seluruh versi course plan, terbaru lebih dulu.

    Setiap versi membawa nomor, status, catatan revisi, dan waktu sehingga
    frontend dapat menampilkan riwayat penolakan/regenerasi.
    """
    records = await service.list_versions(
        workflow_id=workflow_id, owner_id=current_user.id
    )
    return CoursePlanVersionListResponse(
        items=[_to_summary(record) for record in records]
    )


@router.get(
    "/workflows/{workflow_id}/plan/versions/{version}",
    response_model=CoursePlanResponse,
)
async def read_course_plan_version(
    workflow_id: WorkflowIdPath,
    version: PlanVersionPath,
    current_user: User = Depends(instructor_only),
    service: CoursePlanService = Depends(get_course_plan_service),
) -> CoursePlanResponse:
    """Detail satu versi course plan (termasuk versi lama)."""
    record = await service.get_version(
        workflow_id=workflow_id, owner_id=current_user.id, version=version
    )
    return _to_plan(record)


@router.post(
    "/workflows/{workflow_id}/plan/approve",
    response_model=CoursePlanResponse,
)
async def approve_course_plan(
    workflow_id: WorkflowIdPath,
    current_user: User = Depends(instructor_only),
    service: CoursePlanService = Depends(get_course_plan_service),
) -> CoursePlanResponse:
    """Setujui versi terbaru yang berstatus ``DRAFT`` dan lolos validasi.

    ``409 INVALID_REQUEST`` bila versi terbaru bukan ``DRAFT`` atau belum lolos
    validasi — versi lama tidak pernah disetujui lewat endpoint ini. Keputusan
    dosen tercatat sebagai ``WorkflowEvent`` (``WORKFLOW_PLAN_APPROVED``).
    """
    record = await service.approve(
        workflow_id=workflow_id, owner_id=current_user.id
    )
    return _to_plan(record)


@router.post(
    "/workflows/{workflow_id}/plan/reject",
    response_model=CoursePlanResponse,
)
async def reject_course_plan(
    workflow_id: WorkflowIdPath,
    payload: PlanRejectRequest,
    current_user: User = Depends(instructor_only),
    service: CoursePlanService = Depends(get_course_plan_service),
) -> CoursePlanResponse:
    """Tolak versi terbaru dengan catatan revisi wajib.

    Catatan kosong/spasi saja ditolak ``422 INVALID_REQUEST``. Keputusan dosen
    tercatat sebagai ``WorkflowEvent`` (``WORKFLOW_PLAN_REJECTED``) beserta nomor
    versi dan catatannya.
    """
    record = await service.reject(
        workflow_id=workflow_id,
        owner_id=current_user.id,
        notes=payload.notes,
    )
    return _to_plan(record)


# --- Generate / regenerate (BE-14.3) ----------------------------------------


@router.post(
    "/workflows/{workflow_id}/plan",
    response_model=PlanGenerationResponse,
    status_code=202,
)
async def generate_course_plan(
    workflow_id: WorkflowIdPath,
    background: BackgroundTasks,
    current_user: User = Depends(instructor_only),
    service: CoursePlanService = Depends(get_course_plan_service),
    runner: CoursePlanningRunner = Depends(get_course_planning_runner),
) -> PlanGenerationResponse:
    """Mulai penyusunan course plan versi pertama (issue BE-14.3).

    Hanya untuk workflow yang RPS-nya sudah ``ANALYZED`` dan belum memiliki
    course plan. Response ``202`` berarti pekerjaan sudah dijadwalkan;
    client memantau status workflow dan event sampai ``WAITING_FOR_REVIEW``
    atau ``FAILED``. Dua permintaan bersamaan tidak dapat memulai dua run:
    workflow diklaim secara atomik sebelum dijadwalkan.
    """
    workflow = await service.start_planning(
        workflow_id=workflow_id,
        owner_id=current_user.id,
        regenerate=False,
    )
    background.add_task(
        runner,
        workflow_id=workflow.id or "",
        owner_id=current_user.id,
        instruction=None,
    )
    return PlanGenerationResponse(
        workflow_id=workflow.id or "",
        status=workflow.status.value,
        message=GENERATION_MESSAGE,
    )


@router.post(
    "/workflows/{workflow_id}/plan/regenerate",
    response_model=PlanGenerationResponse,
    status_code=202,
)
async def regenerate_course_plan(
    workflow_id: WorkflowIdPath,
    background: BackgroundTasks,
    payload: PlanRegenerateRequest | None = None,
    current_user: User = Depends(instructor_only),
    service: CoursePlanService = Depends(get_course_plan_service),
    runner: CoursePlanningRunner = Depends(get_course_planning_runner),
) -> PlanGenerationResponse:
    """Susun ulang course plan setelah versi terbaru ditolak (issue BE-14.3).

    ``instruction`` opsional; bila kosong, catatan revisi terakhir pada versi
    yang ditolak dipakai sebagai konteks regenerasi. Versi lama tidak diubah —
    hasilnya disimpan sebagai versi baru berstatus ``DRAFT``.
    """
    instruction = payload.instruction if payload is not None else None
    workflow = await service.start_planning(
        workflow_id=workflow_id,
        owner_id=current_user.id,
        regenerate=True,
        instruction=instruction,
    )
    background.add_task(
        runner,
        workflow_id=workflow.id or "",
        owner_id=current_user.id,
        instruction=instruction,
    )
    return PlanGenerationResponse(
        workflow_id=workflow.id or "",
        status=workflow.status.value,
        message=GENERATION_MESSAGE,
    )
