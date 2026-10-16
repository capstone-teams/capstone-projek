"""DTO endpoint RPS (BE-05.1 & BE-05.2).

Kontrak HTTP mengikuti ``docs/02. design/design-api.md`` §6.1 (upload), §6.2
(detail), dan §6.3 (process), dengan dua catatan yang disengaja:

1. **``agent_run_id`` tidak ada pada response process.** design-api §6.3
   menyebutkannya, tetapi Agent Run pada ``agent_runs`` mensyaratkan
   ``course_id`` yang belum ada pada tahap RPS (Course baru dibuat setelah RPS
   dianalisis — data-model §10). Workflow asynchronous beserta Agent Run
   dikerjakan pada BE-08; menampilkan field yang selalu ``null`` akan
   menyesatkan client.
2. **``RPSDetailResponse`` menyertakan ``source_markdown``.** Response §6.2 pada
   dokumen hanya memuat metadata dan status; hasil konversi ikut dikembalikan di
   sini supaya hasil BE-05.2 dapat diperiksa lewat API tanpa membuka database
   (artefak JSON/YAML/tabel tetap berada di storage, bukan di response, karena
   ukurannya besar).

Nama field mengikuti dokumen API (``filename``), bukan nama kolom database
(``file_name``), karena inilah kontrak yang dibaca client.

Catatan import: enum status diambil dari :mod:`src.services.rps.enums` — sumber
tunggal nilai status — sehingga schema tidak mendefinisikan ulang nilainya.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.rps_structured import RPS_SCHEMA_VERSION
from src.services.rps.enums import RPSStatus

__all__ = [
    "RPSDetailResponse",
    "RPSProcessRequest",
    "RPSProcessResponse",
    "RPSUploadResponse",
]


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

    ``has_source_markdown`` dan ``has_source_document`` adalah indikator ringan
    untuk client yang memantau status pemrosesan (mereka yang melakukan polling
    setelah ``POST /process`` menerima 202), sedangkan ``source_markdown``
    memuat hasil konversinya. ``source_document`` — representasi penuh dokumen
    hasil Docling — tidak dikembalikan di sini karena ukurannya besar; ia
    tersedia bagi tahap ekstraksi (BE-08) dan dapat diangkat menjadi endpoint
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
    """

    id: str
    filename: str
    status: RPSStatus
    file_hash: str
    schema_version: str
    created_at: datetime
    updated_at: datetime
    has_source_markdown: bool
    has_source_document: bool
    processing_duration_ms: int | None = None
    processing_error_code: str | None = None
    processing_error_message: str | None = None
    source_markdown: str | None = None


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

    ``202`` berarti konversi **diterima dan dijadwalkan**: ``status`` bernilai
    ``PROCESSING`` dan client memantau perkembangannya lewat
    ``GET /api/v1/rps/{rps_id}`` sampai ``PROCESSED`` atau ``FAILED``.

    ``200`` dengan ``reused: true`` berarti tidak ada pekerjaan yang dijadwalkan
    karena dokumen sudah pernah diproses untuk ``file_hash`` dan
    ``schema_version`` yang sama (acceptance criteria BE-05).
    """

    rps_id: str
    status: RPSStatus
    schema_version: str
    reused: bool
