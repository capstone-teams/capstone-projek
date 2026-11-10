"""Endpoint Moodle verification berbasis workflow (BE-22.2, DL-012).

Menggantikan endpoint verifikasi berbasis course pada API Specification §14.
Router hanya menangani urusan HTTP; read-back, pembandingan, perbaikan, dan
penyimpanan hasil berada di :mod:`src.services.verification` (BE-21.2).

| Method | Path                                                         | Keterangan                     |
| ------ | ------------------------------------------------------------ | ------------------------------ |
| POST   | ``/workflows/{workflow_id}/verifications``                   | jalankan verifikasi (ulang)    |
| GET    | ``/workflows/{workflow_id}/verifications``                   | riwayat hasil verifikasi       |
| GET    | ``/workflows/{workflow_id}/verifications/{verification_id}`` | satu hasil beserta perbedaan   |

Verifikasi dijalankan di dalam request: response ``201`` sudah berisi hasil
akhir setelah perbaikan otomatis (paling banyak
``MOODLE_VERIFICATION_MAX_REPAIRS`` putaran). Seluruh endpoint instructor-only
dan dibatasi workflow milik dosen yang login: workflow atau hasil verifikasi
milik dosen lain menghasilkan 404 yang sama seperti tidak ada, dan mahasiswa
selalu 403. Penolakan prasyarat memakai ``409 INVALID_REQUEST`` dengan kode
alasan pada ``error.details`` (``field = "reason"``).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, status

from src.schemas.errors import ErrorResponse
from src.schemas.verification import (
    DiscrepancyResponse,
    DiscrepancyType,
    VerificationCreateRequest,
    VerificationListResponse,
    VerificationResponse,
    VerificationStatus,
)
from src.services.dependencies import get_verification_service, require_roles
from src.services.user.domain import User
from src.services.user.enums import UserRole
from src.services.user.validation import ID_LENGTH, SHORTUUID_PATTERN
from src.services.verification import Discrepancy, VerificationResultRecord
from src.services.verification.service import VerificationService

router = APIRouter(tags=["Moodle Verification"])

instructor_only = require_roles(UserRole.INSTRUCTOR)

ResourceIdPath = Annotated[
    str,
    Path(min_length=ID_LENGTH, max_length=ID_LENGTH, pattern=SHORTUUID_PATTERN),
]

PRECONDITION_EXAMPLE = {
    "error": {
        "code": "INVALID_REQUEST",
        "message": "Belum ada eksekusi ke Moodle yang dapat diverifikasi.",
        "details": [{"field": "reason", "message": "NO_EXECUTION_TO_VERIFY"}],
    }
}

ERROR_RESPONSES = {
    401: {"model": ErrorResponse, "description": "AUTHENTICATION_FAILED"},
    403: {"model": ErrorResponse, "description": "AUTHORIZATION_DENIED"},
    404: {"model": ErrorResponse, "description": "RESOURCE_NOT_FOUND"},
}

START_RESPONSES = {
    **ERROR_RESPONSES,
    409: {
        "model": ErrorResponse,
        "description": (
            "INVALID_REQUEST: prasyarat tidak terpenuhi (`NO_EXECUTION_TO_VERIFY`, "
            "`EXECUTION_IN_PROGRESS`)"
        ),
        "content": {"application/json": {"example": PRECONDITION_EXAMPLE}},
    },
}


def _to_discrepancy(item: Discrepancy) -> DiscrepancyResponse:
    data = item.to_dict()
    data["type"] = DiscrepancyType(item.type.value)
    return DiscrepancyResponse(**data)


def _to_response(record: VerificationResultRecord) -> VerificationResponse:
    return VerificationResponse(
        verification_id=record.id or "",
        workflow_id=record.workflow_id,
        execution_id=record.execution_id,
        status=VerificationStatus(record.status.value),
        matches=record.matches,
        summary=record.summary,
        discrepancies=[_to_discrepancy(item) for item in record.discrepancies],
        repaired=[_to_discrepancy(item) for item in record.repaired],
        repair_count=record.repair_count,
        repair_rounds=record.repair_rounds,
        error_message=record.error_message,
        verified_at=record.verified_at,
    )


@router.post(
    "/workflows/{workflow_id}/verifications",
    response_model=VerificationResponse,
    status_code=status.HTTP_201_CREATED,
    responses=START_RESPONSES,
)
async def start_verification(
    workflow_id: ResourceIdPath,
    payload: Annotated[VerificationCreateRequest | None, Body()] = None,
    current_user: User = Depends(instructor_only),
    service: VerificationService = Depends(get_verification_service),
) -> VerificationResponse:
    """Verifikasi (ulang) course hasil eksekusi terhadap rencana yang disetujui.

    Moodle dibaca ulang, dibandingkan dengan course plan dan konten ``APPROVED``,
    lalu perbedaan yang dapat diperbaiki diperbaiki otomatis dengan menjalankan
    ulang operasi terkait. Response berisi hasil akhir; status workflow tidak
    diubah. Activity yang ditambahkan langsung di Moodle hanya dilaporkan.
    """
    record = await service.verify(
        workflow_id=workflow_id,
        owner_id=current_user.id,
        execution_id=payload.execution_id if payload is not None else None,
    )
    return _to_response(record)


@router.get(
    "/workflows/{workflow_id}/verifications",
    response_model=VerificationListResponse,
    responses=ERROR_RESPONSES,
)
async def list_verifications(
    workflow_id: ResourceIdPath,
    current_user: User = Depends(instructor_only),
    service: VerificationService = Depends(get_verification_service),
) -> VerificationListResponse:
    """Riwayat hasil verifikasi sebuah workflow, terbaru lebih dulu."""
    records = await service.list_results(
        workflow_id=workflow_id, owner_id=current_user.id
    )
    return VerificationListResponse(items=[_to_response(item) for item in records])


@router.get(
    "/workflows/{workflow_id}/verifications/{verification_id}",
    response_model=VerificationResponse,
    responses=ERROR_RESPONSES,
)
async def read_verification(
    workflow_id: ResourceIdPath,
    verification_id: ResourceIdPath,
    current_user: User = Depends(instructor_only),
    service: VerificationService = Depends(get_verification_service),
) -> VerificationResponse:
    """Satu hasil verifikasi: status, perbedaan, perbaikan, dan waktu."""
    record = await service.get_result(
        workflow_id=workflow_id,
        owner_id=current_user.id,
        verification_id=verification_id,
    )
    return _to_response(record)