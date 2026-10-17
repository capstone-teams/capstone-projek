"""AuthService — mekanisme authentication aplikasi (BE-03.3).

Alur yang disediakan:

1. ``authenticate(identifier, password)`` — memverifikasi kredensial terhadap
   record User dan mengembalikan user yang terautentikasi (atau error domain);
   ``identifier`` boleh berupa **username** maupun **email**;
2. ``issue_access_token(user)`` — membentuk authentication state untuk request
   berikutnya;
3. ``get_authenticated_user(token)`` — memulihkan current user dari token,
   dipakai oleh protected endpoint dan (nantinya) authorization guard BE-03.4.

Authentication hanya menentukan "siapa User ini"; apakah User boleh menjalankan
sebuah operasi adalah tanggung jawab authorization (BE-03.4). Tidak ada logika
Moodle, agent, maupun fitur bisnis di sini.

Catatan field: ``users.username`` adalah atribut Moodle (dipakai saat membuat
user di Moodle) yang juga dapat dipakai login. Kontrak API
``POST /api/v1/auth/login`` mengirim field ``username`` (design-api §5.1) yang
berisi identifier login: username atau email — lihat
:class:`src.schemas.auth.LoginRequest`.
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
from src.services.user.errors import UserValidationError
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

    async def authenticate(self, *, identifier: str, password: str) -> User:
        """Verifikasi kredensial dan kembalikan user yang terautentikasi.

        ``identifier`` boleh berupa **email** maupun **username** (atribut
        Moodle). Email dicoba lebih dulu karena bersifat case-insensitive dan
        merupakan identifier login historis; bila tidak ada yang cocok,
        username dicoba sehingga akun yang username-nya kebetulan berbentuk
        email tetap dapat login.

        Semua penyebab kegagalan menghasilkan error publik yang sama:
        identifier tidak terdaftar, identifier tidak berbentuk email/username
        yang valid, password tidak cocok, user non-aktif, dan user tanpa
        credential lokal (``password`` kosong). Identifier yang salah bentuk
        karena itu tidak boleh menjadi 500 maupun membocorkan perbedaan
        perilaku.
        """
        user = await self._find_user(identifier)

        if user is None:
            # Verifikasi dummy agar waktu respons tidak membocorkan keberadaan user.
            verify_password(password, None)
            raise InvalidCredentialsError("login gagal: identifier tidak terdaftar")

        if not verify_password(password, user.password):
            raise InvalidCredentialsError(
                f"login gagal: password tidak cocok untuk user {user.id}"
            )

        if not user.can_authenticate():
            raise InactiveUserError(
                f"login ditolak: user {user.id} berstatus {user.status.value}"
            )

        return user

    async def _find_user(self, identifier: str) -> User | None:
        """Cari user yang cocok dengan email atau username.

        Identifier dinormalisasi seperlunya oleh masing-masing lookup. Bila
        identifier tidak valid untuk salah satu bentuk, lookup tersebut
        dianggap tidak menemukan apa pun — bukan error — supaya kegagalan
        authentication tetap seragam.

        Bila sebuah nilai cocok dengan email user A sekaligus username user B,
        email diutamakan. Aturan ini deterministik dan menjaga kompatibilitas
        dengan klien yang selama ini mengirim email pada field ``username``.
        """
        if not isinstance(identifier, str):
            return None

        candidate = identifier.strip()
        if not candidate:
            return None

        try:
            user = await self._users.find_user_by_email(candidate)
        except UserValidationError:
            user = None
        if user is not None:
            return user

        try:
            return await self._users.find_user_by_username(candidate)
        except UserValidationError:
            return None

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
