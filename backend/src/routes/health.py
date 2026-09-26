"""Endpoint root dan health check aplikasi.

Router ini hanya menyediakan kontrak HTTP untuk probe infrastruktur
(liveness/readiness) sehingga berada di luar prefix versi API. Tidak boleh ada
logika bisnis, query database, atau pemanggilan service di dalam modul ini.
"""

from fastapi import APIRouter

router = APIRouter(tags=["System"])


@router.get("/")
async def root() -> dict[str, str]:
    """Menandai bahwa service backend berjalan."""
    return {"message": "Moodle Agentic AI Backend"}


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Liveness probe untuk monitoring dan container orchestration."""
    return {"status": "ok"}
