"""Menjalankan pemrosesan RPS di luar siklus request (BE-05.2).

design-api §6.3 menetapkan ``POST /api/v1/rps/{rps_id}/process`` sebagai
operasi *asynchronous*: request hanya menandai dokumen ``PROCESSING`` lalu
kembali, sedangkan konversinya berjalan di belakang layar.

Modul ini adalah tempat konversi itu dijalankan. Dua hal yang membuatnya berbeda
dari sekadar memanggil service di dalam route:

1. **Session database sendiri.** Session milik request sudah ditutup ketika
   response dikirim, sehingga pekerjaan background tidak boleh memakainya.
   Runner membuka session baru dari session factory aplikasi.
2. **Kegagalan tidak dilempar ke client.** Tidak ada client yang menunggu, jadi
   kegagalan dilaporkan lewat **status dokumen** (``FAILED``, yang sudah dicatat
   service) dan log server-side. Exception yang lolos akan menjadi
   "Task exception was never retrieved" dan menghilang tanpa jejak yang berguna.

Catatan cakupan: runner ini berjalan **in-process** (Starlette
``BackgroundTasks``). Itu memadai untuk S0 — request tidak lagi tertahan
konversi — tetapi belum tahan terhadap proses yang mati di tengah jalan. Dua
bentengnya: (a) dokumen yang terlantar dapat diproses ulang setelah
``RPS_PROCESSING_LEASE_SECONDS``, dan (b) Agent Run beserta antrean pekerjaan
yang durable menyusul pada BE-08, yang memang memiliki ``course_id`` sebagai
induk Agent Run.
"""

from __future__ import annotations

import logging

from src.config.database import get_session_factory
from src.services.rps.errors import RPSDomainError
from src.services.rps.service import RPSService

__all__ = ["run_rps_processing"]

logger = logging.getLogger(__name__)


async def run_rps_processing(*, rps_id: str, owner_id: str) -> None:
    """Konversi dokumen RPS yang sudah berstatus ``PROCESSING``.

    Dipanggil sebagai background task setelah response dikirim. Seluruh
    kegagalan ditelan di sini dengan sengaja — bukan karena diabaikan, melainkan
    karena jalur pelaporannya adalah status dokumen dan log, bukan response HTTP
    yang sudah terkirim.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        service = RPSService.from_session(session)
        try:
            result = await service.convert(rps_id=rps_id, owner_id=owner_id)
        except RPSDomainError as exc:
            logger.warning(
                "pemrosesan RPS %s gagal: %s", rps_id, exc.log_message
            )
        except Exception:
            logger.exception("pemrosesan RPS %s gagal di luar error domain", rps_id)
        else:
            logger.info(
                "pemrosesan RPS %s selesai dalam %s ms",
                rps_id,
                result.document.processing_duration_ms,
            )
