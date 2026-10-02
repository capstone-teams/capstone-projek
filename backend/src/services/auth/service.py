"""AuthService — mekanisme authentication aplikasi (BE-03.3).

Alur yang disediakan:

1. ``authenticate(username, password)`` — memverifikasi kredensial terhadap
   record User dan mengembalikan user yang terautentikasi (atau error domain);
2. ``issue_access_token(user)`` — membentuk authentication state untuk request
   berikutnya;
3. ``get_authenticated_user(token)`` — memulihkan current user dari token,
   dipakai oleh protected endpoint dan (nantinya) authorization guard BE-03.4.

Authentication hanya menentukan "siapa User ini"; apakah User boleh menjalankan
sebuah operasi adalah tanggung jawab authorization (BE-03.4). Tidak ada logika
Moodle, agent, maupun fitur bisnis di sini.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.auth.errors import (
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from src.services.auth.passwords import verify_password
from src.services.auth.tokens import create_access_token, decode_access_token
from src.services.user.domain import User
from src.services.user.service import UserService

__all__ = ["AuthService"]


class AuthService:
    """Operasi authentication di atas :class:`UserService`."""

    def __init__(self, user_service: UserService) -> None:
        self._users = user_service

    @classmethod
    def from_session(cls, session: AsyncSession) -> "AuthService":
        """Bangun service dengan User Service di atas session yang diberikan."""
        return cls(UserService.from_session(session))

    async def authenticate(self, *, username: str, password: str) -> User:
        """Verifikasi kredensial dan kembalikan user yang terautentikasi.

        ``username`` mengikuti kontrak API (design-api §5.1 dan dipetakan ke
        ``User.email``, karena email adalah identity attribute pada data model —
        User tidak memiliki atribut username terpisah.

        Semua penyebab kegagalan menghasilkan error publik yang sama: email
        tidak terdaftar, password tidak cocok, user non-aktif, dan user tanpa
        credential lokal (``password_hash`` kosong).
        """
        user = await self._users.find_user_by_email(username)
        if user is None:
            # Verifikasi dummy agar waktu respons tidak membocorkan keberadaan email.
            verify_password(password, None)
            raise InvalidCredentialsError("login gagal: email tidak terdaftar")

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError(
                f"login gagal: password tidak cocok untuk user {user.id}"
            )

        if not user.can_authenticate():
            raise InactiveUserError(
                f"login ditolak: user {user.id} berstatus {user.status.value}"
            )

        return user

    async def issue_access_token(
        self, user: User, *, expires_delta: timedelta | None = None
    ) -> str:
        """Terbitkan access token untuk user yang sudah lolos authentication."""
        if user.id is None:
            raise InvalidCredentialsError("token tidak dapat diterbitkan tanpa identifier user")
        if not user.can_authenticate():
            raise InactiveUserError(
                f"token tidak diterbitkan: user {user.id} berstatus {user.status.value}"
            )
        return create_access_token(user.id, expires_delta=expires_delta)

    async def get_authenticated_user(self, token: str) -> User:
        """Pulihkan current user dari access token.

        Role dan status **selalu** dibaca ulang dari record User, bukan dari
        klaim token: perubahan role langsung berlaku dan client tidak dapat
        menaikkan privilege-nya melalui token.
        """
        user_id = decode_access_token(token)
        user = await self._users.find_user_by_id(user_id)
        if user is None:
            raise InvalidTokenError(f"token valid tetapi user {user_id} tidak ditemukan")
        if not user.can_authenticate():
            raise InactiveUserError(
                f"token ditolak: user {user_id} berstatus {user.status.value}"
            )
        return user
