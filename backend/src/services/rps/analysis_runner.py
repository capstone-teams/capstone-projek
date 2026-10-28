"""Menjalankan analisis RPS di luar siklus request (BE-08.2).

Sama seperti :mod:`src.services.rps.runner` untuk konversi: analisis dipicu oleh
endpoint ``POST /api/v1/rps/{rps_id}/reanalyze`` yang langsung menjawab ``202``,
lalu dikerjakan di background dengan **session database sendiri** (session
request sudah ditutup saat response dikirim).

Kegagalan tidak dilempar ke client — tidak ada client yang menunggu. Hasilnya
dilaporkan lewat status dokumen (``ANALYZED`` atau ``FAILED`` beserta
``processing_error_code``/``processing_error``) dan log server-side, sehingga
kegagalan analisis tidak menghentikan server (acceptance criteria BE-08.2).
"""

from __future__ import annotations

import logging

from src.config.database import get_session_factory
from src.services.rps.errors import RPSDomainError
from src.services.rps.service import RPSService

__all__ = ["run_rps_analysis"]

logger = logging.getLogger(__name__)


async def run_rps_analysis(*, rps_id: str, owner_id: str) -> None:
    """Analisis dokumen RPS yang sudah berstatus ``ANALYZING``.

    Dipanggil sebagai background task setelah response ``202`` dikirim. Seluruh
    kegagalan ditelan di sini dengan sengaja: jalur pelaporannya adalah status
    dokumen dan log, bukan response HTTP yang sudah terkirim.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        service = RPSService.from_session(session)
        try:
            await service.analyze(rps_id=rps_id, owner_id=owner_id)
        except RPSDomainError as exc:
            logger.warning("analisis RPS %s gagal: %s", rps_id, exc.log_message)
        except Exception:
            logger.exception("analisis RPS %s gagal di luar error domain", rps_id)
        else:
            logger.info("analisis RPS %s selesai", rps_id)
