"""Rute stub untuk kontrak endpoint yang belum diimplementasikan (BE-06.4).

Tujuannya semata menerbitkan bentuk request/response pada OpenAPI agar frontend
dapat membangun halaman beserta mock sebelum endpoint-nya selesai (design-api
§6.4–§6.7, §16, §17). **Setiap** handler di sini menjawab ``501`` dengan
amplop error standar (design-api §18) — tidak ada data palsu yang bisa
dikonsumsi client.

Rute stub ini berumur pendek dan **harus** dibuang saat implementasi aslinya
mendarat:

- ``/rps`` (GET), ``/rps/{id}/analysis`` → BE-08.3
- ``/workflows``, ``/workflows/{id}/events`` → BE-11.3

``POST /rps/{id}/reanalyze`` sudah diimplementasikan pada
:mod:`src.routes.rps` oleh BE-08.2, sehingga stub-nya sudah dibuang.

Otorisasi tidak dipasang di sini: stub tidak menyentuh data siapa pun. Endpoint
aslinya wajib instructor-only seperti endpoint RPS pada :mod:`src.routes.rps`
(contoh yang sudah rilis: :mod:`src.routes.instructors`, BE-10.2).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path
from fastapi.responses import JSONResponse

from src.schemas.contract import (
    RPSAnalysisResponse,
    RPSListResponse,
    WorkflowEventListResponse,
    WorkflowListResponse,
)
from src.services.user.validation import ID_LENGTH, SHORTUUID_PATTERN

router = APIRouter(tags=["Contract (stub)"])

NOT_IMPLEMENTED_CODE = "NOT_IMPLEMENTED"
NOT_IMPLEMENTED_MESSAGE = (
    "Endpoint ini baru tersedia sebagai kontrak pada OpenAPI dan belum "
    "diimplementasikan. Gunakan mock pada frontend sampai endpoint aslinya rilis."
)
NOT_IMPLEMENTED_RESPONSE = {
    501: {
        "description": "Kontrak sudah terbit, implementasi belum ada.",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": NOT_IMPLEMENTED_CODE,
                        "message": NOT_IMPLEMENTED_MESSAGE,
                        "details": [],
                    }
                }
            }
        },
    }
}

# Sama dengan :mod:`src.routes.rps`: identifier path adalah ShortUUID, sehingga
# bentuk yang salah ditolak sebelum menyentuh layer lain.
RpsIdPath = Annotated[
    str,
    Path(min_length=ID_LENGTH, max_length=ID_LENGTH, pattern=SHORTUUID_PATTERN),
]
WorkflowIdPath = Annotated[
    str,
    Path(min_length=ID_LENGTH, max_length=ID_LENGTH, pattern=SHORTUUID_PATTERN),
]


def _not_implemented() -> JSONResponse:
    """Jawab ``501`` dengan amplop error design-api §18."""
    return JSONResponse(
        status_code=501,
        content={
            "error": {
                "code": NOT_IMPLEMENTED_CODE,
                "message": NOT_IMPLEMENTED_MESSAGE,
                "details": [],
            }
        },
    )


@router.get(
    "/rps",
    response_model=RPSListResponse,
    summary="Daftar RPS dosen (kontrak, BE-08.3)",
    responses=NOT_IMPLEMENTED_RESPONSE,
)
async def list_rps_stub() -> RPSListResponse:
    """``GET /api/v1/rps`` — daftar RPS milik dosen yang login."""
    return _not_implemented()


@router.get(
    "/rps/{rps_id}/analysis",
    response_model=RPSAnalysisResponse,
    summary="Hasil analisis RPS (kontrak, BE-08.3)",
    responses=NOT_IMPLEMENTED_RESPONSE,
)
async def get_rps_analysis_stub(rps_id: RpsIdPath) -> RPSAnalysisResponse:
    """``GET /api/v1/rps/{rps_id}/analysis`` — RPS Structured Data hasil analisis."""
    return _not_implemented()


@router.get(
    "/workflows",
    response_model=WorkflowListResponse,
    summary="Daftar workflow (kontrak, BE-11.3)",
    responses=NOT_IMPLEMENTED_RESPONSE,
)
async def list_workflows_stub() -> WorkflowListResponse:
    """``GET /api/v1/workflows`` — daftar workflow milik dosen yang login."""
    return _not_implemented()


@router.get(
    "/workflows/{workflow_id}/events",
    response_model=WorkflowEventListResponse,
    summary="Riwayat event workflow (kontrak, BE-11.3)",
    responses=NOT_IMPLEMENTED_RESPONSE,
)
async def list_workflow_events_stub(workflow_id: WorkflowIdPath) -> WorkflowEventListResponse:
    """``GET /api/v1/workflows/{workflow_id}/events`` — riwayat event workflow.

    Bentuk tiap item sama dengan frame ``WS /api/v1/ws/workflows/{workflow_id}``.
    """
    return _not_implemented()
