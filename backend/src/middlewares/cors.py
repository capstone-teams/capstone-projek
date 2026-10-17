"""CORS untuk frontend development (BE-06.2).

Frontend Vite berjalan pada origin berbeda dari backend
(``http://localhost:3000`` vs ``http://localhost:8000``), sehingga browser
mengirim preflight sebelum request yang memakai header ``Authorization`` atau
``Content-Type: application/json``. Middleware ini mengizinkan origin yang
dikonfigurasi melalui ``CORS_ORIGINS`` dan menolak preflight dari origin lain.

Keputusan desain:

- **Daftar origin eksplisit**, bukan wildcard, sehingga origin yang tidak
  terdaftar benar-benar ditolak (acceptance criteria BE-06.2). Nilai berasal
  dari environment, bukan hardcode; origin production ditentukan kemudian.
- **``allow_credentials=False``**: authentication memakai bearer token di header
  ``Authorization``, bukan cookie, sehingga browser tidak perlu mengirim
  credential otomatis. Ini juga mencegah kombinasi wildcard/credential yang
  berbahaya.
- **Header yang diizinkan eksplisit**, termasuk ``Idempotency-Key``
  (design-api §21) supaya fitur berikutnya tidak langsung gagal preflight.
- **``WWW-Authenticate`` diekspos** agar frontend dapat membaca challenge 401.

Modul ini hanya berisi konfigurasi middleware; tidak ada logika domain dan tidak
ada route.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings

__all__ = [
    "CORS_ALLOWED_HEADERS",
    "CORS_ALLOWED_METHODS",
    "CORS_MAX_AGE_SECONDS",
    "register_cors",
]

logger = logging.getLogger(__name__)

# Method yang dipakai API (termasuk OPTIONS untuk preflight dan HEAD untuk probe).
CORS_ALLOWED_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")

# Header yang boleh dikirim browser. Idempotency-Key sudah dipakai client untuk
# operasi idempoten (design-api §21), sehingga harus lolos preflight sejak awal.
CORS_ALLOWED_HEADERS = (
    "Accept",
    "Authorization",
    "Content-Type",
    "Idempotency-Key",
)

# Browser boleh meng-cache hasil preflight selama 10 menit.
CORS_MAX_AGE_SECONDS = 600


def register_cors(application: FastAPI, origins: list[str] | None = None) -> None:
    """Pasang CORSMiddleware dengan origin dari konfigurasi aplikasi.

    ``origins`` hanya dipakai pengujian; aplikasi selalu membaca
    ``settings.CORS_ORIGINS`` pada saat ``create_app()`` dijalankan. Daftar kosong
    berarti tidak ada frontend yang diizinkan — bukan "izinkan semua" — dan
    dicatat sebagai peringatan agar salah konfigurasi terlihat saat startup.
    """
    allowed_origins = list(settings.CORS_ORIGINS if origins is None else origins)
    if not allowed_origins:
        logger.warning(
            "CORS_ORIGINS kosong: tidak ada origin frontend yang diizinkan. "
            "Set CORS_ORIGINS pada environment development."
        )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=list(CORS_ALLOWED_METHODS),
        allow_headers=list(CORS_ALLOWED_HEADERS),
        expose_headers=["WWW-Authenticate"],
        max_age=CORS_MAX_AGE_SECONDS,
    )
