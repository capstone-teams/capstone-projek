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

Stub kontrak BE-06.4 sudah tidak ada: seluruh endpoint yang pernah dijanjikan
telah diimplementasikan, dan endpoint workflow dipindahkan ke
:mod:`src.routes.workflows` oleh BE-11.3.
"""

from fastapi import APIRouter

from src.routes.admin import router as admin_router
from src.routes.auth import router as auth_router
from src.routes.course_plans import router as course_plans_router
from src.routes.courses import router as courses_router
from src.routes.executions import router as executions_router
from src.routes.health import router as health_router
from src.routes.instructors import router as instructors_router
from src.routes.moodle import router as moodle_router
from src.routes.rps import router as rps_router
from src.routes.workflows import router as workflows_router

# Base URL endpoint bisnis, mengikuti dokumen design-api.
API_V1_PREFIX = "/api/v1"

api_router = APIRouter(prefix=API_V1_PREFIX)
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(instructors_router)
api_router.include_router(moodle_router)
api_router.include_router(rps_router)
api_router.include_router(course_plans_router)
api_router.include_router(executions_router)
api_router.include_router(courses_router)
api_router.include_router(workflows_router)

__all__ = [
    "API_V1_PREFIX",
    "admin_router",
    "api_router",
    "auth_router",
    "course_plans_router",
    "courses_router",
    "executions_router",
    "health_router",
    "instructors_router",
    "moodle_router",
    "rps_router",
    "workflows_router",
]