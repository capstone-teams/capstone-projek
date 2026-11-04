"""DTO endpoint RPS (BE-05, BE-08.2 & BE-08.3).

Kontrak HTTP mengikuti ``docs/02. design/design-api.md`` §6.1 (upload), §6.2
(detail), §6.3 (process), §6.4 (hasil analisis), §6.5 (daftar), dan §6.6
(reanalyze), dengan satu catatan yang disengaja:

1. **``agent_run_id`` tidak ada pada response process.** design-api §6.3
   menyebutkannya, tetapi Agent Run pada ``agent_runs`` mensyaratkan
   ``course_id`` yang belum ada pada tahap RPS (Course baru dibuat setelah RPS
   dianalisis — data-model §10). Workflow asynchronous beserta Agent Run
   dikerjakan pada BE-08; menampilkan field yang selalu ``null`` akan
   menyesatkan client.

Detail dokumen hanya membawa indikator ``has_source_document``; JSON hasil
Docling berukuran besar dan tidak dikembalikan di response. Markdown tidak lagi
dibentuk dari RPS (DL-008, BE-13), sehingga tidak ada field markdown pada
kontrak ini.

Nama field mengikuti dokumen API (``filename``), bukan nama kolom database
(``file_name``), karena inilah kontrak yang dibaca client.

Catatan import: enum status diambil dari :mod:`src.services.rps.enums` — sumber
tunggal nilai status — sehingga schema tidak mendefinisikan ulang nilainya.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.rps_structured import RPS_SCHEMA_VERSION, RPSStructuredData
from src.services.rps.enums import RPSStatus

__all__ = [
    "RPSAnalysisResponse",
    "RPSDetailResponse",
    "RPSListItem",
    "RPSListResponse",
    "RPSProcessRequest",
    "RPSProcessResponse",
    "RPSReanalyzeResponse",
    "RPSUploadResponse",
]

# Contoh identifier ShortUUID pada dokumentasi OpenAPI.
RPS_ID_EXAMPLE = "kP3nQ7vRtYx2bM8sLdWfZa"


class RPSUploadResponse(BaseModel):
    """Response ``POST /api/v1/rps`` (design-api §6.1).

    ``deduplicated`` menandai unggahan dokumen yang isinya sudah pernah
    diunggah untuk versi skema yang sama: response-nya memuat dokumen yang sudah
    ada (HTTP 200), bukan dokumen baru (HTTP 201).
    """

    id: str
    filename: str
    status: RPSStatus
    file_hash: str
    schema_version: str
    deduplicated: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "kP3nQ7vRtYx2bM8sLdWfZa",
                "filename": "rps-basis-data.pdf",
                "status": "UPLOADED",
                "file_hash": "9f2c...c41d",
                "schema_version": RPS_SCHEMA_VERSION,
                "deduplicated": False,
            }
        }
    )


class RPSDetailResponse(BaseModel):
    """Response ``GET /api/v1/rps/{rps_id}`` (design-api §6.2).

    ``has_source_document`` adalah indikator ringan untuk client yang memantau
    status pemrosesan (mereka yang melakukan polling setelah
    ``POST /process`` menerima 202). ``source_document`` — representasi penuh
    dokumen hasil Docling — tidak dikembalikan di sini karena ukurannya besar;
    ia tersedia bagi tahap ekstraksi (BE-08) dan dapat diangkat menjadi endpoint
    tersendiri bila client membutuhkannya.

    ``processing_duration_ms`` adalah durasi konversi yang tercatat, berguna
    untuk evaluasi performa (issue #98).

    ``processing_error_code`` dan ``processing_error_message`` terisi hanya bila
    statusnya ``FAILED``: kode error mengikuti design-api §18 (mis.
    ``RPS_PROCESSING_FAILED``) dan pesannya adalah alasan publik yang aman
    ditampilkan. Ini yang membuat kegagalan konversi tetap "dapat dipahami"
    meskipun konversinya berjalan di background dan tidak lagi muncul pada
    response request.

    Field ``structured_data`` tidak dikembalikan di sini — hasil ekstraksi
    terstruktur adalah ranah BE-08 melalui endpoint analisis.

    ``workflow_id`` adalah workflow orkestrasi yang menjalankan pemrosesan RPS
    ini (BE-11.2); ``null`` untuk dokumen yang diunggah sebelum workflow ada dan
    belum pernah diproses.
    """

    id: str
    filename: str
    status: RPSStatus
    file_hash: str
    schema_version: str
    created_at: datetime
    updated_at: datetime
    has_source_document: bool
    workflow_id: str | None = Field(
        default=None,
        description="Workflow orkestrasi RPS ini; null bila belum ada.",
    )
    processing_duration_ms: int | None = None
    processing_error_code: str | None = None
    processing_error_message: str | None = None


class RPSProcessRequest(BaseModel):
    """Body opsional ``POST /api/v1/rps/{rps_id}/process``.

    ``schema_version`` boleh dikosongkan: secara default dokumen diproses untuk
    versi skema yang tercatat padanya. Mengirim versi lain berarti meminta
    pemrosesan ulang untuk skema yang lebih baru — hasil lama tidak berlaku lagi
    (lihat :meth:`src.services.rps.service.RPSService.begin_processing`).
    """

    schema_version: str | None = Field(default=None, min_length=1, max_length=50)


class RPSProcessResponse(BaseModel):
    """Response ``POST /api/v1/rps/{rps_id}/process`` (design-api §6.3).

    ``202`` berarti pemrosesan **diterima dan dijadwalkan**: ``status`` bernilai
    ``PROCESSING`` dan client memantau perkembangannya lewat
    ``GET /api/v1/rps/{rps_id}`` sampai ``ANALYZED`` atau ``FAILED``. Sejak
    BE-11.2 konversi dilanjutkan analisis dalam workflow yang sama, sehingga
    status akhir pemrosesan adalah ``ANALYZED`` (bukan berhenti di
    ``PROCESSED``).

    ``200`` dengan ``reused: true`` berarti konversi tidak dijadwalkan karena
    dokumen sudah pernah diproses untuk ``file_hash`` dan ``schema_version``
    yang sama (acceptance criteria BE-05); analisis yang belum ada tetap
    dijalankan pada workflow baru.

    ``workflow_id`` adalah workflow orkestrasi yang menjalankan rangkaian tahap.
    Client memakainya untuk memantau event lewat ``GET /workflows/{id}`` dan
    ``GET /workflows/{id}/events`` (BE-11.3).
    """

    rps_id: str
    status: RPSStatus
    schema_version: str
    reused: bool
    workflow_id: str


class RPSReanalyzeResponse(BaseModel):
    """Response ``POST /api/v1/rps/{rps_id}/reanalyze`` (design-api §6.6).

    ``202`` berarti analisis ulang **dijadwalkan** dari ``source_document`` yang
    sudah tersimpan — Docling tidak dijalankan lagi. ``workflow_id`` adalah
    workflow yang menjalankan analisis; client memantau hasilnya lewat
    ``GET /api/v1/rps/{rps_id}`` sampai status ``ANALYZED`` atau ``FAILED``,
    lalu membaca hasilnya lewat ``GET /api/v1/rps/{rps_id}/analysis`` (§6.4).
    """

    rps_id: str
    workflow_id: str
    status: RPSStatus = RPSStatus.ANALYZING

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rps_id": "kP3nQ7vRtYx2bM8sLdWfZa",
                "workflow_id": "q7RtYx2bM8sLdWfZaKp3nQ",
                "status": "ANALYZING",
            }
        }
    )


class RPSListItem(BaseModel):
    """Satu baris daftar RPS milik dosen yang login (design-api §6.5).

    ``workflow_id`` terisi setelah analisis dijadwalkan (BE-08.2) atau setelah
    orkestrator BE-11.2 menghubungkan RPS dengan workflow-nya.
    """

    id: str
    filename: str
    status: RPSStatus
    schema_version: str
    workflow_id: str | None = Field(
        default=None,
        description="Workflow analisis RPS ini; null bila belum ada.",
    )
    has_source_document: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": RPS_ID_EXAMPLE,
                "filename": "rps-basis-data.pdf",
                "status": "PROCESSED",
                "schema_version": "2.0",
                "workflow_id": None,
                "has_source_document": True,
                "created_at": "2026-10-21T08:00:00Z",
                "updated_at": "2026-10-21T08:00:42Z",
            }
        }
    )


class RPSListResponse(BaseModel):
    """Response ``GET /api/v1/rps`` (design-api §6.5)."""

    items: list[RPSListItem] = Field(default_factory=list, description="RPS milik dosen.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": RPS_ID_EXAMPLE,
                        "filename": "rps-basis-data.pdf",
                        "status": "PROCESSED",
                        "schema_version": "2.0",
                        "workflow_id": None,
                        "has_source_document": True,
                        "created_at": "2026-10-21T08:00:00Z",
                        "updated_at": "2026-10-21T08:00:42Z",
                    }
                ]
            }
        }
    )


class RPSAnalysisResponse(BaseModel):
    """Response ``GET /api/v1/rps/{rps_id}/analysis`` (design-api §6.4).

    ``data`` adalah RPS Structured Data lengkap (content-schema §6.2) — identitas
    mata kuliah, CPL, CPMK, Sub-CPMK, rencana mingguan, penilaian, dan referensi.
    ``analyzed_at`` adalah waktu analisis yang menghasilkan data tersebut.
    """

    rps_id: str
    analyzed_at: datetime = Field(description="Waktu analisis yang menghasilkan data ini.")
    data: RPSStructuredData

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rps_id": RPS_ID_EXAMPLE,
                "analyzed_at": "2026-10-21T08:01:10Z",
                "data": {
                    "schema_version": "2.0",
                    "course": {"name": "Basis Data", "code": "IF123", "credits": 3},
                    "cpmk": [{"id": "CPMK-1", "description": "Merancang basis data relasional"}],
                    "weeks": [{"week": 1, "topics": ["Pengenalan Basis Data"]}],
                },
            }
        }
    )
