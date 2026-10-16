"""Endpoint RPS: unggah, detail, dan pemrosesan (BE-05).

Router ini hanya menangani urusan HTTP: kontrak endpoint, dependency, validasi
bentuk input (path parameter), dan response DTO. Validasi berkas, penyimpanan,
serta konversi dokumen berada di :mod:`src.services.rps`.

Authorization mengikuti design-api §22: seluruh operasi RPS adalah
instructor-only (``Upload RPS``, ``Process RPS``, ``View RPS Analysis`` — Student
``No``). Guard-nya satu policy yang dipakai ulang oleh ketiga endpoint, sama
seperti pola ``admin_only`` pada :mod:`src.routes.admin`.

Kontrak pemrosesan mengikuti design-api §6.3: ``POST /rps/{id}/process``
menjadwalkan konversi dan langsung menjawab ``202`` dengan status ``PROCESSING``.
Konversinya dijalankan oleh :mod:`src.services.rps.runner` **setelah** response
dikirim, sehingga request tidak tertahan selama model Docling bekerja; client
memantau ``GET /rps/{id}`` sampai statusnya ``PROCESSED`` atau ``FAILED``.
Dokumen yang sudah diproses untuk versi skema yang sama tidak dijadwalkan ulang
dan dijawab ``200`` + ``reused: true``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Path,
    Response,
    UploadFile,
    status,
)

from src.config.settings import get_settings
from src.schemas.rps import (
    RPSDetailResponse,
    RPSProcessRequest,
    RPSProcessResponse,
    RPSUploadResponse,
)
from src.services.dependencies import (
    RPSProcessingRunner,
    get_rps_processing_runner,
    get_rps_service,
    require_roles,
)
from src.services.rps.domain import RPSDocument
from src.services.rps.enums import RPSStatus
from src.services.rps.service import RPSService
from src.services.user.domain import User
from src.services.user.enums import UserRole
from src.services.user.validation import ID_LENGTH, SHORTUUID_PATTERN

router = APIRouter(prefix="/rps", tags=["RPS"])

# Policy instructor-only, didefinisikan sekali dan dipakai ulang oleh seluruh
# endpoint pada router ini (design-api §22).
instructor_only = require_roles(UserRole.INSTRUCTOR)

# Identifier pada path adalah ShortUUID (``rps.id``). Polanya divalidasi di layer
# HTTP supaya identifier yang salah bentuk menghasilkan 422 tanpa menyentuh
# service maupun database.
RpsIdPath = Annotated[
    str,
    Path(min_length=ID_LENGTH, max_length=ID_LENGTH, pattern=SHORTUUID_PATTERN),
]


def _to_detail(document: RPSDocument) -> RPSDetailResponse:
    """Petakan domain RPS ke DTO detail."""
    return RPSDetailResponse(
        id=document.id or "",
        filename=document.file_name,
        status=document.status,
        file_hash=document.file_hash,
        schema_version=document.schema_version,
        created_at=document.created_at,
        updated_at=document.updated_at,
        has_source_markdown=bool(document.source_markdown),
        has_source_document=bool(document.source_document),
        processing_duration_ms=document.processing_duration_ms,
        processing_error_code=document.processing_error_code,
        processing_error_message=document.processing_error,
        source_markdown=document.source_markdown,
    )


@router.post("", response_model=RPSUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_rps(
    response: Response,
    file: Annotated[UploadFile, File(description="Dokumen RPS (PDF)")],
    current_user: User = Depends(instructor_only),
    service: RPSService = Depends(get_rps_service),
) -> RPSUploadResponse:
    """Unggah dokumen RPS dan simpan beserta ``file_hash``-nya.

    Isi berkas dibaca dengan batas ``RPS_MAX_UPLOAD_BYTES + 1`` byte: ukuran
    maksimum tetap diputuskan layer service (satu tempat untuk kebijakan itu),
    sementara pembacaan tanpa batas ke memori dihindari.

    Response ``201`` untuk dokumen baru dan ``200`` bila isi dokumen yang sama
    sudah pernah diunggah untuk versi skema yang sama (``deduplicated: true``).
    """
    content = await file.read(get_settings().rps_max_upload_bytes + 1)
    result = await service.upload_rps(
        owner_id=current_user.id,
        file_name=file.filename or "",
        content=content,
    )
    if result.deduplicated:
        response.status_code = status.HTTP_200_OK

    document = result.document
    return RPSUploadResponse(
        id=document.id or "",
        filename=document.file_name,
        status=document.status,
        file_hash=document.file_hash,
        schema_version=document.schema_version,
        deduplicated=result.deduplicated,
    )


@router.get("/{rps_id}", response_model=RPSDetailResponse)
async def read_rps(
    rps_id: RpsIdPath,
    current_user: User = Depends(instructor_only),
    service: RPSService = Depends(get_rps_service),
) -> RPSDetailResponse:
    """Detail dokumen RPS milik instructor yang meminta.

    Endpoint inilah yang dipantau client setelah pemrosesan dijadwalkan
    (``status`` berubah ``PROCESSING`` → ``PROCESSED``/``FAILED``). Ketika
    statusnya ``FAILED``, ``processing_error_code`` dan
    ``processing_error_message`` menjelaskan penyebabnya. Dokumen milik
    instructor lain menghasilkan 404 ``RESOURCE_NOT_FOUND`` yang sama seperti
    dokumen yang tidak ada.
    """
    document = await service.get_rps(rps_id=rps_id, owner_id=current_user.id)
    return _to_detail(document)


@router.post(
    "/{rps_id}/process",
    response_model=RPSProcessResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def process_rps(
    rps_id: RpsIdPath,
    response: Response,
    background: BackgroundTasks,
    current_user: User = Depends(instructor_only),
    service: RPSService = Depends(get_rps_service),
    runner: RPSProcessingRunner = Depends(get_rps_processing_runner),
    payload: RPSProcessRequest | None = None,
) -> RPSProcessResponse:
    """Jadwalkan konversi dokumen RPS menjadi ``source_markdown`` (Docling).

    ``202`` + ``status: PROCESSING`` berarti konversi diterima dan berjalan di
    background. ``200`` + ``reused: true`` berarti tidak ada yang dijadwalkan
    karena dokumen sudah diproses untuk ``file_hash`` + ``schema_version`` yang
    sama (idempotency BE-05).

    Kegagalan konversi tidak muncul pada response ini — tidak ada client yang
    menunggu pekerjaan background. Hasilnya terlihat pada ``GET /rps/{id}``:
    status ``FAILED``, dengan penyebab sebenarnya hanya tercatat server-side.
    """
    start = await service.begin_processing(
        rps_id=rps_id,
        owner_id=current_user.id,
        schema_version=payload.schema_version if payload is not None else None,
    )

    if start.reused:
        response.status_code = status.HTTP_200_OK
        return RPSProcessResponse(
            rps_id=start.document.id or "",
            status=start.document.status,
            schema_version=start.document.schema_version,
            reused=True,
        )

    background.add_task(
        runner,
        rps_id=start.document.id or "",
        owner_id=current_user.id,
    )
    return RPSProcessResponse(
        rps_id=start.document.id or "",
        status=RPSStatus.PROCESSING,
        schema_version=start.document.schema_version,
        reused=False,
    )
