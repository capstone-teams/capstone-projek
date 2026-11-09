"""Endpoint review konten hasil generation (BE-19.2).

Router ini hanya menangani urusan HTTP: kontrak endpoint, dependency, dan
pemetaan domain → DTO. Aturan keputusan review dan penulisan ``WorkflowEvent``
berada di :mod:`src.services.content.service`.

Endpoint berbasis workflow (DL-011), mengikuti Sequence Diagram Review
Generated Content (Proposal §3.4.6):

- ``GET  /workflows/{workflow_id}/contents`` — daftar konten + filter
- ``GET  /workflows/{workflow_id}/contents/{content_id}`` — detail satu versi
- ``GET  …/contents/{content_id}/versions`` — riwayat versi
- ``POST …/contents/generate`` — hasilkan konten seluruh/beberapa minggu
- ``POST …/contents/regenerate`` — regenerasi scope COURSE/MINGGU/ITEM
- ``POST …/contents/approve`` — setujui konten
- ``POST …/contents/reject`` — tolak dengan catatan revisi

Seluruh endpoint instructor-only dan dibatasi workflow milik dosen yang login
(design-api §22; workflow dosen lain menghasilkan 404 yang sama seperti workflow
tidak ada). Mahasiswa selalu 403. Contoh response keempat jenis konten ada pada
dokumentasi OpenAPI endpoint detail.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query

from src.schemas.content_generation import (
    ContentGenerateRequest,
    ContentGenerationResponse,
    ContentRegenerateRequest,
)
from src.schemas.content_review import (
    CONTENT_DETAIL_EXAMPLES,
    ContentApproveRequest,
    ContentDecisionResponse,
    ContentDetail,
    ContentListResponse,
    ContentRejectRequest,
    ContentSummary,
    ContentValidationDetail,
    ContentValidationSummary,
    ContentVersionListResponse,
    ContentVersionSummary,
)
from src.services.content import (
    ApprovalStatus,
    ContentKind,
    ContentRecord,
    ContentReviewService,
)
from src.services.content.generation import (
    ContentGenerationService,
    ContentJob,
)
from src.services.dependencies import (
    ContentGenerationRunner,
    get_content_generation_runner,
    get_content_generation_service,
    get_content_service,
    require_roles,
)
from src.services.user.domain import User
from src.services.user.enums import UserRole
from src.services.user.validation import ID_LENGTH, SHORTUUID_PATTERN

router = APIRouter(tags=["Contents"])

#: Konten hanya dapat dibaca/direview dosen (design-api §22).
instructor_only = require_roles(UserRole.INSTRUCTOR)

WorkflowIdPath = Annotated[
    str,
    Path(min_length=ID_LENGTH, max_length=ID_LENGTH, pattern=SHORTUUID_PATTERN),
]

ContentIdPath = Annotated[
    str,
    Path(min_length=ID_LENGTH, max_length=ID_LENGTH, pattern=SHORTUUID_PATTERN),
]


def _to_validation_summary(
    record: ContentRecord,
) -> ContentValidationSummary | None:
    """Ringkasan hasil validasi terbaru, atau ``None`` bila belum divalidasi."""
    validation = record.validation
    if validation is None:
        return None
    return ContentValidationSummary(
        status=validation.status,
        score=validation.score,
        retry_count=validation.retry_count,
        validated_at=validation.validated_at,
    )


def _to_summary(record: ContentRecord) -> ContentSummary:
    """Petakan satu versi konten ke item daftar."""
    return ContentSummary(
        id=record.id,
        content_key=record.content_key,
        kind=record.kind,
        week_number=record.week_number,
        title=record.title,
        version=record.version,
        status=record.status,
        revision_notes=record.revision_notes,
        validation=_to_validation_summary(record),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _to_detail(record: ContentRecord) -> ContentDetail:
    """Petakan satu versi konten ke response detail."""
    validation = record.validation
    return ContentDetail(
        **_to_summary(record).model_dump(exclude={"validation"}),
        workflow_id=record.workflow_id,
        course_plan_id=record.course_plan_id,
        course_plan_week_id=record.course_plan_week_id,
        content_data=record.content_data,
        content_markdown=record.content_markdown,
        prompt_version=record.prompt_version,
        model_name=record.model_name,
        validation=(
            ContentValidationDetail(
                status=validation.status,
                score=validation.score,
                retry_count=validation.retry_count,
                validated_at=validation.validated_at,
                checks=validation.checks,
                errors=validation.errors,
                warnings=validation.warnings,
                created_at=validation.created_at,
            )
            if validation is not None
            else None
        ),
    )


def _to_version(record: ContentRecord) -> ContentVersionSummary:
    """Petakan satu versi konten ke baris riwayat versi."""
    return ContentVersionSummary(
        id=record.id,
        version=record.version,
        status=record.status,
        revision_notes=record.revision_notes,
        validation=_to_validation_summary(record),
        created_at=record.created_at,
    )


@router.get(
    "/workflows/{workflow_id}/contents",
    response_model=ContentListResponse,
)
async def list_contents(
    workflow_id: WorkflowIdPath,
    week_number: int | None = Query(
        default=None, ge=1, description="Filter satu minggu."
    ),
    content_type: ContentKind | None = Query(
        default=None, description="Filter jenis konten."
    ),
    status: ApprovalStatus | None = Query(
        default=None, description="Filter status approval."
    ),
    current_user: User = Depends(instructor_only),
    service: ContentReviewService = Depends(get_content_service),
) -> ContentListResponse:
    """Daftar konten workflow, versi terbaru tiap jenis, urut minggu.

    Setiap item memuat ringkasan hasil validasi. Filter yang tidak cocok
    menghasilkan daftar kosong; workflow yang tidak ada/bukan milik dosen
    menghasilkan ``404 RESOURCE_NOT_FOUND``.
    """
    records = await service.list_contents(
        workflow_id=workflow_id,
        owner_id=current_user.id,
        week_number=week_number,
        content_type=content_type,
        status=status,
    )
    return ContentListResponse(items=[_to_summary(record) for record in records])


@router.get(
    "/workflows/{workflow_id}/contents/{content_id}",
    response_model=ContentDetail,
    responses={
        200: {
            "description": "Detail konten; isi ``content_data`` bergantung jenis.",
            "content": {"application/json": {"examples": CONTENT_DETAIL_EXAMPLES}},
        }
    },
)
async def read_content(
    workflow_id: WorkflowIdPath,
    content_id: ContentIdPath,
    current_user: User = Depends(instructor_only),
    service: ContentReviewService = Depends(get_content_service),
) -> ContentDetail:
    """Detail satu versi konten beserta isi dan hasil validasi lengkap."""
    record = await service.get_content(
        workflow_id=workflow_id, owner_id=current_user.id, content_id=content_id
    )
    return _to_detail(record)


@router.get(
    "/workflows/{workflow_id}/contents/{content_id}/versions",
    response_model=ContentVersionListResponse,
)
async def list_content_versions(
    workflow_id: WorkflowIdPath,
    content_id: ContentIdPath,
    current_user: User = Depends(instructor_only),
    service: ContentReviewService = Depends(get_content_service),
) -> ContentVersionListResponse:
    """Riwayat seluruh versi konten, terbaru lebih dulu.

    ``content_id`` boleh menunjuk versi mana pun; riwayat dikelompokkan lewat
    ``content_key`` sehingga versi lama tetap dapat dibuka.
    """
    records = await service.list_versions(
        workflow_id=workflow_id, owner_id=current_user.id, content_id=content_id
    )
    return ContentVersionListResponse(items=[_to_version(record) for record in records])


@router.post(
    "/workflows/{workflow_id}/contents/approve",
    response_model=ContentDecisionResponse,
)
async def approve_contents(
    workflow_id: WorkflowIdPath,
    payload: ContentApproveRequest | None = None,
    current_user: User = Depends(instructor_only),
    service: ContentReviewService = Depends(get_content_service),
) -> ContentDecisionResponse:
    """Setujui versi terbaru konten yang lolos validasi.

    Body boleh kosong (seluruh konten), berisi ``content_ids``, atau
    ``week_number``. Versi lama tidak pernah disetujui: id versi lama dipetakan
    ke versi terbarunya. ``409 INVALID_REQUEST`` bila ada konten yang belum
    lolos validasi, sudah ditolak, atau sudah dieksekusi. Keputusan tercatat
    sebagai ``WorkflowEvent`` (``WORKFLOW_CONTENTS_APPROVED``).
    """
    selection = payload or ContentApproveRequest()
    records = await service.approve(
        workflow_id=workflow_id,
        owner_id=current_user.id,
        content_ids=selection.content_ids,
        week_number=selection.week_number,
    )
    return ContentDecisionResponse(
        workflow_id=workflow_id,
        decision="APPROVED",
        items=[_to_summary(record) for record in records],
    )


@router.post(
    "/workflows/{workflow_id}/contents/reject",
    response_model=ContentDecisionResponse,
)
async def reject_contents(
    workflow_id: WorkflowIdPath,
    payload: ContentRejectRequest,
    current_user: User = Depends(instructor_only),
    service: ContentReviewService = Depends(get_content_service),
) -> ContentDecisionResponse:
    """Tolak versi terbaru konten dengan catatan revisi wajib.

    Catatan kosong/spasi saja ditolak ``422 INVALID_REQUEST``. Pilihan konten
    sama dengan approve: ``content_ids``, ``week_number``, atau seluruh konten.
    Keputusan tercatat sebagai ``WorkflowEvent`` (``WORKFLOW_CONTENTS_REJECTED``)
    beserta catatan revisinya.
    """
    records = await service.reject(
        workflow_id=workflow_id,
        owner_id=current_user.id,
        notes=payload.notes,
        content_ids=payload.content_ids,
        week_number=payload.week_number,
    )
    return ContentDecisionResponse(
        workflow_id=workflow_id,
        decision="REJECTED",
        items=[_to_summary(record) for record in records],
    )


# --- Generate / regenerate (BE-19.3) ----------------------------------------

GENERATION_MESSAGE = (
    "Generation konten dijadwalkan; pantau status workflow dan event untuk hasilnya."
)
REGENERATION_MESSAGE = (
    "Regenerasi konten dijadwalkan; pantau status workflow dan event untuk hasilnya."
)


@router.post(
    "/workflows/{workflow_id}/contents/generate",
    response_model=ContentGenerationResponse,
    status_code=202,
)
async def generate_contents(
    workflow_id: WorkflowIdPath,
    background: BackgroundTasks,
    payload: ContentGenerateRequest | None = None,
    current_user: User = Depends(instructor_only),
    service: ContentGenerationService = Depends(get_content_generation_service),
    runner: ContentGenerationRunner = Depends(get_content_generation_runner),
) -> ContentGenerationResponse:
    """Mulai generation konten untuk seluruh minggu atau minggu terpilih.

    Hanya untuk workflow yang course plan terbarunya ``APPROVED``. Jenis konten
    mengikuti snapshot Activity Configuration versi rencana tersebut. Response
    ``202`` berarti pekerjaan sudah dijadwalkan; dua permintaan bersamaan tidak
    dapat memulai dua run karena workflow diklaim secara atomik.
    """
    request = payload or ContentGenerateRequest()
    week_numbers = (
        None if request.weeks == "all" else tuple(request.weeks)
    )
    workflow = await service.start(
        workflow_id=workflow_id,
        owner_id=current_user.id,
        job=ContentJob(week_numbers=week_numbers),
    )
    background.add_task(
        runner,
        workflow_id=workflow.id or "",
        owner_id=current_user.id,
        week_numbers=week_numbers,
    )
    return ContentGenerationResponse(
        workflow_id=workflow.id or "",
        status=workflow.status.value,
        message=GENERATION_MESSAGE,
    )


@router.post(
    "/workflows/{workflow_id}/contents/regenerate",
    response_model=ContentGenerationResponse,
    status_code=202,
)
async def regenerate_contents(
    workflow_id: WorkflowIdPath,
    background: BackgroundTasks,
    payload: ContentRegenerateRequest,
    current_user: User = Depends(instructor_only),
    service: ContentGenerationService = Depends(get_content_generation_service),
    runner: ContentGenerationRunner = Depends(get_content_generation_runner),
) -> ContentGenerationResponse:
    """Regenerasi konten dengan scope ``COURSE``, ``MINGGU``, atau ``ITEM``.

    Catatan revisi wajib diisi dan ikut dikirim ke prompt regenerasi. Versi lama
    tidak diubah: hasilnya disimpan sebagai versi baru pada ``content_key`` yang
    sama, dan hanya target pada scope yang disentuh.
    """
    week_numbers = (
        (payload.week_number,) if payload.week_number is not None else None
    )
    workflow = await service.start(
        workflow_id=workflow_id,
        owner_id=current_user.id,
        job=ContentJob(
            week_numbers=week_numbers,
            content_id=payload.content_id,
            scope=payload.scope,
            notes=payload.notes,
        ),
    )
    background.add_task(
        runner,
        workflow_id=workflow.id or "",
        owner_id=current_user.id,
        week_numbers=week_numbers,
        content_id=payload.content_id,
        scope=payload.scope.value,
        notes=payload.notes,
    )
    return ContentGenerationResponse(
        workflow_id=workflow.id or "",
        status=workflow.status.value,
        scope=payload.scope,
        message=REGENERATION_MESSAGE,
    )
