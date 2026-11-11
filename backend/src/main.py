"""Entry point aplikasi FastAPI.

Modul ini hanya bertugas merakit aplikasi: menyiapkan lifespan hook dan
meregistrasikan exception handler global serta router. Kontrak HTTP berada di
``src/routes`` dan logika bisnis berada di ``src/services``, sehingga tidak boleh
ada route individual maupun logika bisnis di sini.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware

from src.config.database import dispose_engine
from src.config.settings import settings
from src.middlewares.cors import register_cors
from src.middlewares.error_handlers import register_exception_handlers
from src.routes import api_router, health_router
from src.services.auth.tokens import warn_if_secret_is_weak
from src.services.workflow.reconciliation import reconcile_interrupted_runs

logger = logging.getLogger(__name__)


async def _close_interrupted_runs() -> None:
    """Tutup run yang mati bersama proses sebelumnya; kegagalan tidak memblokir startup."""
    try:
        await reconcile_interrupted_runs()
    except Exception:  # pragma: no cover - hanya jalur infrastruktur
        logger.exception("gagal menutup workflow yang terputus")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Lifecycle startup/shutdown aplikasi.

    Disediakan khusus untuk resource infrastruktur (contoh: database engine,
    connection pool, HTTP client). Logika bisnis tidak boleh dijalankan di sini.
    """
    warn_if_secret_is_weak()
    await _close_interrupted_runs()
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    """Membangun dan mengonfigurasi instance aplikasi FastAPI."""
    application = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )
    # CORS dipasang sebelum router/exception handler lain dieksekusi, sehingga
    # header CORS tetap ada pada response sukses maupun error (401/422).
    register_cors(application)
    # Response JSON bisa besar (analisis RPS, konten mingguan). Kompresi di
    # sini memangkas waktu transfer tanpa mengubah kontrak endpoint. Level 6
    # dipilih karena pada payload JSON rasionya sama dengan level 9 tetapi
    # ~2x lebih murah di CPU (diukur pada ~80 KB payload).
    application.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=6)
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(api_router)
    return application


app = create_app()
