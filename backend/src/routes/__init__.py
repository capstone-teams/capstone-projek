"""Registri terpusat seluruh router aplikasi.

Router baru tidak diregistrasikan langsung di ``src.main``, melainkan
ditambahkan di sini agar ``create_app()`` hanya perlu menyertakan router yang
sudah teragregasi.

- ``health_router``: endpoint infrastruktur, tanpa prefix versi.
- ``api_router``: agregator seluruh router bisnis di bawah ``/api/v1`` sesuai
  spesifikasi API. Router fitur baru cukup ditambahkan dengan
  ``api_router.include_router(<feature_router>)``.
"""

from fastapi import APIRouter

from src.routes.health import router as health_router

# Base URL endpoint bisnis, mengikuti dokumen design-api.
API_V1_PREFIX = "/api/v1"

api_router = APIRouter(prefix=API_V1_PREFIX)

__all__ = ["API_V1_PREFIX", "api_router", "health_router"]
