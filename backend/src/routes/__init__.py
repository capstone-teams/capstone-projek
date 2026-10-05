"""Registri terpusat seluruh router aplikasi.

Router baru tidak diregistrasikan langsung di ``src.main``, melainkan
ditambahkan di sini agar ``create_app()`` hanya perlu menyertakan router yang
sudah teragregasi.

- ``health_router``: endpoint infrastruktur, tanpa prefix versi.
- ``api_router``: agregator seluruh router bisnis di bawah ``/api/v1`` sesuai
  spesifikasi API. Router fitur baru cukup ditambahkan dengan
  ``api_router.include_router(<feature_router>)``.

Router fitur hanya mendeklarasikan prefix miliknya sendiri (contoh:
``/auth``); prefix ``/api/v1`` dimiliki oleh ``api_router``.
"""

from fastapi import APIRouter

from src.routes.admin import router as admin_router
from src.routes.auth import router as auth_router
from src.routes.health import router as health_router

# Base URL endpoint bisnis, mengikuti dokumen design-api.
API_V1_PREFIX = "/api/v1"

api_router = APIRouter(prefix=API_V1_PREFIX)
api_router.include_router(auth_router)
api_router.include_router(admin_router)

__all__ = ["API_V1_PREFIX", "admin_router", "api_router", "auth_router", "health_router"]
