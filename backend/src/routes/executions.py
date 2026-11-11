"""Endpoint eksekusi Moodle berbasis workflow (BE-17.2, BE-22.2, DL-012).

Router ini hanya menangani urusan HTTP: kontrak endpoint, dependency, dan
pemetaan domain → DTO. Pemeriksaan prasyarat, pembuatan ``MoodleExecution``, dan
penulisan event berada di :mod:`src.services.execution`, sedangkan tahap
``EXECUTING_TO_MOODLE`` dijalankan orkestrator di background.

| Method | Path                                                              | Keterangan                    |
| ------ | ----------------------------------------------------------------- | ----------------------------- |
| POST   | ``/workflows/{workflow_id}/executions``                           | mulai ``STRUCTURE``/``FULL``  |
| GET    | ``/workflows/{workflow_id}/executions``                           | riwayat eksekusi              |
| GET    | ``/workflows/{workflow_id}/executions/{execution_id}``            | status, operasi, read-back    |
| POST   | ``/workflows/{workflow_id}/executions/{execution_id}/retry``      | ulangi operasi gagal          |

Seluruh endpoint instructor-only dan dibatasi workflow milik dosen yang login
(design-api §22): workflow/eksekusi dosen lain menghasilkan 404 yang sama
seperti tidak ada, dan mahasiswa selalu 403. Penolakan prasyarat memakai
``409 INVALID_REQUEST`` dengan kode alasan pada ``error.details``
(``field = "reason"``), mengikuti BE-17.1.

Cakupan ``FULL`` (BE-22.2) memakai prasyarat dan alur yang sama dengan
``STRUCTURE``; bedanya detail eksekusi memuat satu operasi per jenis konten per
minggu (learning material, learning resource, assignment, quiz), termasuk
operasi ``SKIPPED`` untuk jenis yang nonaktif atau belum disetujui. Verifikasi
hasil eksekusi ada di :mod:`src.routes.verifications`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Path, status

from src.schemas.errors import ErrorResponse
from src.schemas.execution import (
    ExecutionCreateRequest,
    ExecutionDetailResponse,
    ExecutionListResponse,
    ExecutionOperationResponse,
    ExecutionResponse,
    ExecutionScope,
    ExecutionStatus,
    ExecutionSummary,
    OperationStatus,
    OperationType,
)
from src.services.dependencies import (
    ExecutionRunner,
    get_execution_runner,
    get_execution_service,
    require_roles,
)
from src.services.execution import ExecutionRecord, ExecutionService
from src.services.user.domain import User
from src.services.user.enums import UserRole
from src.services.user.validation import ID_LENGTH, SHORTUUID_PATTERN

router = APIRouter(tags=["Moodle Execution"])

#: Eksekusi hanya dapat dijalankan/dipantau dosen (design-api §22).
instructor_only = require_roles(UserRole.INSTRUCTOR)

WorkflowIdPath = Annotated[
    str,
    Path(min_length=ID_LENGTH, max_length=ID_LENGTH, pattern=SHORTUUID_PATTERN),
]

ExecutionIdPath = Annotated[
    str,
    Path(min_length=ID_LENGTH, max_length=ID_LENGTH, pattern=SHORTUUID_PATTERN),
]

#: Contoh penolakan prasyarat: kode alasan stabil dari BE-17.1.
PRECONDITION_EXAMPLE = {
    "error": {
        "code": "INVALID_REQUEST",
        "message": "Course plan terbaru belum disetujui.",
        "details": [{"field": "reason", "message": "PLAN_NOT_APPROVED"}],
    }
}

ERROR_RESPONSES = {
    401: {"model": ErrorResponse, "description": "AUTHENTICATION_FAILED"},
    403: {"model": ErrorResponse, "description": "AUTHORIZATION_DENIED"},
    404: {"model": ErrorResponse, "description": "RESOURCE_NOT_FOUND"},
    409: {
        "model": ErrorResponse,
        "description": (
            "INVALID_REQUEST: prasyarat tidak terpenuhi (`PLAN_NOT_APPROVED`, "
            "`MOODLE_TARGET_NOT_SET`, `MOODLE_UNAVAILABLE`, "
            "`EXECUTION_IN_PROGRESS`) atau status eksekusi tidak mengizinkan operasi"
        ),
        "content": {"application/json": {"example": PRECONDITION_EXAMPLE}},
    },
}


def _to_summary(execution: ExecutionRecord) -> ExecutionSummary:
    summary = execution.summary
    return ExecutionSummary(
        total=summary.total,
        success=summary.success,
        failed=summary.failed,
        skipped=summary.skipped,
    )


def _to_operation(operation) -> ExecutionOperationResponse:
    return ExecutionOperationResponse(
        operation_id=operation.id or "",
        operation_type=OperationType(operation.operation_type.value),
        status=OperationStatus(operation.status.value),
        idempotency_key=operation.idempotency_key,
        week_number=operation.week_number,
        content_id=operation.content_id,
        title=operation.title,
        moodle_object_id=operation.moodle_object_id,
        error_message=operation.error_message,
        retry_count=operation.retry_count,
    )


def _to_response(execution: ExecutionRecord) -> ExecutionResponse:
    """Petakan eksekusi domain ke bentuk status ringkas (POST/retry/riwayat)."""
    return ExecutionResponse(
        execution_id=execution.id or "",
        workflow_id=execution.workflow_id,
        course_plan_id=execution.course_plan_id,
        scope=ExecutionScope(execution.scope.value),
        status=ExecutionStatus(execution.status.value),
        moodle_course_id=execution.moodle_course_id,
        summary=_to_summary(execution),
        error_message=execution.error_message,
        created_at=execution.created_at,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
    )


def _to_detail(execution: ExecutionRecord) -> ExecutionDetailResponse:
    """Petakan eksekusi domain ke detail: operasi per minggu/konten + read-back."""
    return ExecutionDetailResponse(
        **_to_response(execution).model_dump(),
        readback=execution.readback,
        operations=[_to_operation(operation) for operation in execution.operations],
    )


@router.post(
    "/workflows/{workflow_id}/executions",
    response_model=ExecutionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=ERROR_RESPONSES,
)
async def start_execution(
    workflow_id: WorkflowIdPath,
    payload: ExecutionCreateRequest,
    background: BackgroundTasks,
    current_user: User = Depends(instructor_only),
    service: ExecutionService = Depends(get_execution_service),
    runner: ExecutionRunner = Depends(get_execution_runner),
) -> ExecutionResponse:
    """Mulai eksekusi course plan ke Moodle (BE-17.2, BE-22.2).

    ``STRUCTURE`` membuat section mingguan; ``FULL`` membuat section beserta
    seluruh konten ``APPROVED``. Response ``202`` berisi ``execution_id`` dan
    status awal ``PENDING``; client memantau status workflow (§16) dan detail
    eksekusi sampai ``SUCCESS``/``FAILED``. Prasyarat yang tidak terpenuhi
    ditolak ``409`` dengan kode alasan, sebelum pekerjaan dijadwalkan.
    """
    start = (
        service.start_full
        if payload.scope is ExecutionScope.FULL
        else service.start_structure
    )
    execution = await start(workflow_id=workflow_id, owner_id=current_user.id)
    background.add_task(
        runner,
        workflow_id=workflow_id,
        owner_id=current_user.id,
        execution_id=execution.id or "",
    )
    return _to_response(execution)


@router.get(
    "/workflows/{workflow_id}/executions",
    response_model=ExecutionListResponse,
    responses=ERROR_RESPONSES,
)
async def list_executions(
    workflow_id: WorkflowIdPath,
    current_user: User = Depends(instructor_only),
    service: ExecutionService = Depends(get_execution_service),
) -> ExecutionListResponse:
    """Riwayat eksekusi sebuah workflow, terbaru lebih dulu (issue BE-17.2)."""
    executions = await service.list_executions(
        workflow_id=workflow_id, owner_id=current_user.id
    )
    return ExecutionListResponse(
        items=[_to_response(execution) for execution in executions]
    )


@router.get(
    "/workflows/{workflow_id}/executions/{execution_id}",
    response_model=ExecutionDetailResponse,
    responses=ERROR_RESPONSES,
)
async def read_execution(
    workflow_id: WorkflowIdPath,
    execution_id: ExecutionIdPath,
    current_user: User = Depends(instructor_only),
    service: ExecutionService = Depends(get_execution_service),
) -> ExecutionDetailResponse:
    """Detail eksekusi: status, ringkasan, operasi, dan read-back.

    Setiap operasi menampilkan minggu, jenis, judul, status,
    ``moodle_object_id`` bila berhasil, dan ``error_message`` publik bila gagal
    atau alasan bila ``SKIPPED`` (BE-17.2, BE-22.2).
    """
    execution = await service.get_execution(
        workflow_id=workflow_id,
        owner_id=current_user.id,
        execution_id=execution_id,
    )
    return _to_detail(execution)


@router.post(
    "/workflows/{workflow_id}/executions/{execution_id}/retry",
    response_model=ExecutionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=ERROR_RESPONSES,
)
async def retry_execution(
    workflow_id: WorkflowIdPath,
    execution_id: ExecutionIdPath,
    background: BackgroundTasks,
    current_user: User = Depends(instructor_only),
    service: ExecutionService = Depends(get_execution_service),
    runner: ExecutionRunner = Depends(get_execution_runner),
) -> ExecutionResponse:
    """Ulangi hanya operasi yang gagal pada eksekusi yang sama (issue BE-17.2).

    Hanya eksekusi berstatus ``FAILED`` dengan operasi gagal yang dapat diulang;
    operasi yang sudah berhasil tidak dijalankan ulang. Status response kembali
    ``PENDING`` karena pekerjaan dijadwalkan di background.
    """
    execution = await service.retry_failed(
        workflow_id=workflow_id,
        owner_id=current_user.id,
        execution_id=execution_id,
    )
    background.add_task(
        runner,
        workflow_id=workflow_id,
        owner_id=current_user.id,
        execution_id=execution.id or "",
    )
    return _to_response(execution)