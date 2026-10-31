"""Port analisis RPS untuk tahap ekstraksi (BE-08.2).

Tahap ini mengubah YAML hasil serialisasi :mod:`src.services.rps.yaml_export`
menjadi RPS Structured Data memakai service analisis BE-09.2
(:func:`src.services.analysis.service.analyze_rps`). Service RPS bergantung pada
port :data:`RPSAnalyzer`, bukan pada modul analisis secara langsung, sehingga
pengujian dapat menggantinya tanpa memanggil model bahasa.

Adapter di file ini juga menerjemahkan kegagalan service analisis menjadi
:class:`~src.services.rps.errors.RPSAnalysisFailedError` — satu tipe error
domain RPS yang membawa kode ``LLM_GENERATION_FAILED`` (design-api §18) beserta
alasan publik yang disimpan pada dokumen.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from src.schemas.rps_structured import RPSStructuredData
from src.services.analysis.service import RPSAnalysisError, analyze_rps
from src.services.rps.errors import RPSAnalysisFailedError

__all__ = ["RPSAnalyzer", "analyze_document"]

#: Fungsi yang mengubah YAML RPS menjadi RPS Structured Data tervalidasi.
RPSAnalyzer = Callable[[str], Awaitable[RPSStructuredData]]


async def analyze_document(rps_yaml: str) -> RPSStructuredData:
    """Analisis YAML RPS memakai service analisis BE-09.2.

    ``RPSAnalysisError`` sudah memuat alasan yang aman ditampilkan (mis.
    "Layanan model tidak merespons tepat waktu."), jadi pesannya diteruskan
    sebagai ``public_reason``. Penyebab teknis tetap dicatat server-side oleh
    service analisis.
    """
    try:
        return await analyze_rps(rps_yaml)
    except RPSAnalysisError as exc:
        raise RPSAnalysisFailedError(
            f"analisis RPS gagal (reason={exc.reason_code}, attempts={exc.attempts})",
            public_reason=str(exc) or None,
        ) from exc
