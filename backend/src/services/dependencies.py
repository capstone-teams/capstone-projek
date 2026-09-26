"""Dependency provider untuk layer HTTP (FastAPI).

``backend/README.md`` melarang ``src/routes/`` mengimpor SQLAlchemy dan
membangun session sendiri, tetapi belum menetapkan di mana provider dependency
berada (dibiarkan terbuka sampai database session didefinisikan pada BE-02).
Penempatan yang dipilih: **di dalam layer `services/`**, karena layer inilah
pemegang ``Session`` dan pemilik operasi domain — router cukup memakai
``Depends(...)``.

Pemakaian FastAPI di modul ini terbatas pada primitif dependency (``Depends``,
``HTTPBearer``): tidak ada ``Request``/``Response``, tidak ada ``HTTPException``,
dan tidak ada logika bisnis di sini. Guard authorization (BE-03.4) juga berada
di sini sebagai *factory* — :func:`require_roles` — karena bentuknya adalah
dependency: keputusan allow/deny-nya sendiri tetap milik layer domain
(:class:`~src.services.auth.authorization.RolePolicy`).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session_factory
from src.services.auth.authorization import RolePolicy
from src.services.auth.errors import InvalidTokenError
from src.services.auth.service import AuthService
from src.services.user.domain import User
from src.services.user.enums import UserRole
from src.services.user.service import UserService

__all__ = [
    "bearer_scheme",
    "get_auth_service",
    "get_current_user",
    "get_db_session",
    "get_user_service",
    "require_roles",
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


def require_roles(*roles: UserRole | str) -> Callable[..., Awaitable[User]]:
    """Dependency factory: batasi sebuah endpoint pada role tertentu (BE-03.4).

    Mengembalikan dependency yang bisa dipasang pada endpoint mana pun:

    ```python
    from src.services.dependencies import require_roles

    @router.post("", dependencies=[Depends(require_roles(UserRole.INSTRUCTOR))])
    async def protected_operation(...): ...
    ```

    Satu role untuk single-role restriction (``require_roles(UserRole.ADMIN)``)
    atau beberapa role untuk multiple-role restriction
    (``require_roles(UserRole.INSTRUCTOR, UserRole.STUDENT)``).

    Urutannya disengaja: dependency ini me-resolve current user lebih dulu,
    sehingga request tanpa authentication berhenti di 401
    ``AUTHENTICATION_FAILED`` dan hanya user terautentikasi yang role-nya
    dievaluasi (403 ``AUTHORIZATION_DENIED``). Karena berupa dependency FastAPI,
    authorization selesai **sebelum** handler endpoint dijalankan. Sebagai
    handler, ia juga mengembalikan current user sehingga pemanggil tidak perlu
    me-resolve-nya dua kali (FastAPI meng-cache ``get_current_user`` per
    request).

    Policy divalidasi saat factory dipanggil (import/wiring time), jadi policy
    yang salah — misalnya tanpa role atau memakai role tidak dikenal —
    langsung gagal, bukan menghasilkan 403 yang menyesatkan saat runtime.
    """
    policy = RolePolicy.for_roles(*roles)

    async def require_role(current_user: User = Depends(get_current_user)) -> User:
        return policy.enforce(current_user)

    return require_role
