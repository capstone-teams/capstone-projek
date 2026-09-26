"""Dependency provider untuk layer HTTP (FastAPI).

``backend/README.md`` melarang ``src/routes/`` mengimpor SQLAlchemy dan
membangun session sendiri, tetapi belum menetapkan di mana provider dependency
berada (dibiarkan terbuka sampai database session didefinisikan pada BE-02).
Penempatan yang dipilih: **di dalam layer `services/`**, karena layer inilah
pemegang ``Session`` dan pemilik operasi domain — router cukup memakai
``Depends(...)``.

Pemakaian FastAPI di modul ini terbatas pada primitif dependency (``Depends``,
``HTTPBearer``): tidak ada ``Request``/``Response``, tidak ada ``HTTPException``,
dan tidak ada logika bisnis di sini.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session_factory
from src.services.auth.errors import InvalidTokenError
from src.services.auth.service import AuthService
from src.services.user.domain import User
from src.services.user.service import UserService

__all__ = [
    "bearer_scheme",
    "get_auth_service",
    "get_current_user",
    "get_db_session",
    "get_user_service",
]

# auto_error=False: token yang hilang atau skema header yang salah ditangani
# sebagai error domain (401 AUTHENTICATION_FAILED) oleh exception handler,
# bukan oleh response default FastAPI.
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Access token dari POST /api/v1/auth/login",
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Satu ``AsyncSession`` per request; di-rollback bila request gagal."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def get_user_service(session: AsyncSession = Depends(get_db_session)) -> UserService:
    """User Service untuk endpoint yang menjalankan operasi User."""
    return UserService.from_session(session)


def get_auth_service(session: AsyncSession = Depends(get_db_session)) -> AuthService:
    """Auth Service untuk endpoint authentication."""
    return AuthService.from_session(session)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: AuthService = Depends(get_auth_service),
) -> User:
    """Current user dari header ``Authorization: Bearer <token>``.

    Reusable untuk seluruh protected endpoint (dan authorization guard BE-03.4):
    endpoint cukup menambahkan ``current_user: User = Depends(get_current_user)``.
    """
    token = credentials.credentials if credentials is not None else ""
    if not token:
        raise InvalidTokenError("request tanpa access token")

    return await service.get_authenticated_user(token)
