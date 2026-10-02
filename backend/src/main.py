"""Entry point aplikasi FastAPI.

Modul ini hanya bertugas merakit aplikasi: menyiapkan lifespan hook dan
meregistrasikan exception handler global serta router. Kontrak HTTP berada di
``src/routes`` dan logika bisnis berada di ``src/services``, sehingga tidak boleh
ada route individual maupun logika bisnis di sini.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config.database import dispose_engine
from src.config.settings import settings
from src.middlewares.error_handlers import register_exception_handlers
from src.routes import api_router, health_router
from src.services.auth.tokens import warn_if_secret_is_weak


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Lifecycle startup/shutdown aplikasi.

    Disediakan khusus untuk resource infrastruktur (contoh: database engine,
    connection pool, HTTP client). Logika bisnis tidak boleh dijalankan di sini.
    """
    warn_if_secret_is_weak()
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    """Membangun dan mengonfigurasi instance aplikasi FastAPI."""
    application = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(api_router)
    return application


app = create_app()
