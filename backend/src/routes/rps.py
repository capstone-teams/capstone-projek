"""Endpoint RPS: unggah, detail, pemrosesan (BE-05), analisis (BE-08.2), serta
daftar dan hasil analisis (BE-08.3).

Router ini hanya menangani urusan HTTP: kontrak endpoint, dependency, validasi
bentuk input (path parameter), dan response DTO. Validasi berkas, penyimpanan,
konversi, serta analisis dokumen berada di :mod:`src.services.rps`.

Authorization mengikuti design-api §22: seluruh operasi RPS adalah
instructor-only (``Upload RPS``, ``Process RPS``, ``View RPS Analysis`` — Student
``No``). Guard-nya satu policy yang dipakai ulang oleh seluruh endpoint, sama
seperti pola ``admin_only`` pada :mod:`src.routes.admin`.

Kontrak pemrosesan mengikuti design-api §6.3: ``POST /rps/{id}/process``
menjadwalkan konversi dan langsung menjawab ``202`` dengan status ``PROCESSING``.
Konversinya dijalankan oleh :mod:`src.services.rps.runner` **setelah** response
dikirim, sehingga request tidak tertahan selama model Docling bekerja; client
memantau ``GET /rps/{id}`` sampai statusnya ``PROCESSED`` atau ``FAILED``.
Dokumen yang sudah diproses untuk versi skema yang sama tidak dijadwalkan ulang
dan dijawab ``200`` + ``reused: true``.

Kontrak reanalyze mengikuti design-api §6.6: ``POST /rps/{id}/reanalyze``
menjadwalkan analisis ulang dari ``source_document`` (Docling tidak dijalankan
lagi) dan langsung menjawab ``202`` dengan status ``ANALYZING`` beserta
``workflow_id``. Analisisnya dijalankan
:mod:`src.services.rps.analysis_runner`; kegagalannya terbaca lewat polling
sebagai ``FAILED`` + ``processing_error_code``/``processing_error_message``.

Endpoint baca analisis mengikuti design-api §6.4/§6.5: ``GET /rps`` hanya
memuat dokumen milik dosen yang login, dan ``GET /rps/{id}/analysis``
mengembalikan RPS Structured Data utuh untuk RPS ``ANALYZED``. Keduanya
instructor-only; dokumen milik dosen lain menghasilkan 404 yang sama seperti
dokumen tidak ada.
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
    RPSAnalysisResponse,
    RPSDetailResponse,
    RPSListItem,
    RPSListResponse,
    RPSProcessRequest,
    RPSProcessResponse,
    RPSReanalyzeResponse,
    RPSUploadResponse,
)
from src.schemas.rps_structured import RPSStructuredData
from src.services.dependencies import (
    RPSAnalysisRunner,
    RPSProcessingRunner,
    get_rps_analysis_runner,
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
        has_source_document=bool(document.source_document),
        processing_duration_ms=document.processing_duration_ms,
        processing_error_code=document.processing_error_code,
        processing_error_message=document.processing_error,
    )


def _to_list_item(document: RPSDocument) -> RPSListItem:
    """Petakan domain RPS ke satu baris daftar (design-api §6.5)."""
    return RPSListItem(
        id=document.id or "",
        filename=document.file_name,
        status=document.status,
        schema_version=document.schema_version,
        workflow_id=document.workflow_id,
        has_source_document=bool(document.source_document),
        created_at=document.created_at,
        updated_at=document.updated_at,
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


@router.get("", response_model=RPSListResponse)
async def list_rps(
    current_user: User = Depends(instructor_only),
    service: RPSService = Depends(get_rps_service),
) -> RPSListResponse:
    """Daftar RPS milik dosen yang login (design-api §6.5).

    Hanya dokumen milik peminta yang dikembalikan — scoping owner dilakukan
    query repository, bukan dengan memfilter hasil di layer HTTP. Item memuat
    ``status`` kanonik (termasuk ``ANALYZING``/``ANALYZED``), ``workflow_id``
    bila analisis pernah dijadwalkan, dan ``has_source_document`` sebagai
    indikator ringan tanpa mengirim JSON Docling yang besar.
    """
    documents = await service.list_rps(owner_id=current_user.id)
    return RPSListResponse(items=[_to_list_item(document) for document in documents])


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


@router.get("/{rps_id}/analysis", response_model=RPSAnalysisResponse)
async def read_rps_analysis(
    rps_id: RpsIdPath,
    current_user: User = Depends(instructor_only),
    service: RPSService = Depends(get_rps_service),
) -> RPSAnalysisResponse:
    """Hasil analisis RPS milik instructor yang meminta (design-api §6.4).

    ``data`` adalah RPS Structured Data utuh yang tersimpan pada
    ``rps.structured_data`` — bukan ringkasan terpisah — sehingga client dan
    database memakai kontrak yang sama. RPS yang belum dianalisis menghasilkan
    422 ``INVALID_REQUEST``; RPS milik dosen lain menghasilkan 404 yang sama
    seperti dokumen yang tidak ada.
    """
    document = await service.get_analysis(
        rps_id=rps_id, owner_id=current_user.id
    )
    return RPSAnalysisResponse(
        rps_id=document.id or "",
        analyzed_at=document.analyzed_at,
        data=RPSStructuredData.model_validate(document.structured_data),
    )


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
    """Jadwalkan konversi dokumen RPS menjadi ``source_document`` (JSON Docling).

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


@router.post(
    "/{rps_id}/reanalyze",
    response_model=RPSReanalyzeResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reanalyze_rps(
    rps_id: RpsIdPath,
    background: BackgroundTasks,
    current_user: User = Depends(instructor_only),
    service: RPSService = Depends(get_rps_service),
    runner: RPSAnalysisRunner = Depends(get_rps_analysis_runner),
) -> RPSReanalyzeResponse:
    """Jadwalkan analisis ulang RPS dari ``source_document`` (design-api §6.6).

    ``202`` + status ``ANALYZING`` berarti analisis diterima dan berjalan di
    background; Docling **tidak** dijalankan lagi karena inputnya YAML yang
    dibentuk dari JSON konversi yang tersimpan. Client memantau
    ``GET /rps/{id}`` sampai ``ANALYZED`` atau ``FAILED``, lalu membaca hasilnya
    lewat ``GET /rps/{id}/analysis``.

    Dokumen yang belum dikonversi (``source_document`` kosong) ditolak ``422
    INVALID_REQUEST``; dokumen yang sedang diproses/dianalisis ``409
    INVALID_REQUEST``. Hanya dosen pemilik RPS yang boleh meminta — dokumen
    milik dosen lain menghasilkan 404 yang sama seperti dokumen tidak ada.
    """
    start = await service.begin_analysis(
        rps_id=rps_id,
        owner_id=current_user.id,
        force=True,
    )
    background.add_task(
        runner,
        rps_id=start.document.id or "",
        owner_id=current_user.id,
    )
    return RPSReanalyzeResponse(
        rps_id=start.document.id or "",
        workflow_id=start.workflow_id,
        status=RPSStatus.ANALYZING,
    )
