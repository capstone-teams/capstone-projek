"""Error authentication (BE-03.3) dan authorization (BE-03.4).

Authentication menjawab "siapa User ini?" dan gagalnya dipetakan oleh
``src/middlewares`` ke HTTP 401 dengan kode ``AUTHENTICATION_FAILED``.
Authorization menjawab "bolehkah User ini menjalankan operation ini?" dan
gagalnya dipetakan ke HTTP 403 dengan kode ``AUTHORIZATION_DENIED``
(lihat ``docs/02. design/design-api.md`` §18 dan §19).

Pesan publik authentication sengaja **identik** untuk seluruh penyebab kegagalan
— email tidak terdaftar, password salah, user tidak aktif, maupun user tanpa
credential lokal — supaya response tidak dapat dipakai melakukan *user
enumeration*. Detail penyebab tetap dicatat server-side melalui ``log_message``.
"""

from __future__ import annotations

from collections.abc import Iterable

from src.services.user.enums import UserRole


class AuthDomainError(Exception):
    """Base error authentication/authorization."""

    error_code = "AUTHENTICATION_FAILED"
    status_code = 401
    public_message = "Autentikasi gagal."
    # Hanya 401 yang menyertakan challenge header ``WWW-Authenticate: Bearer``;
    # 403 bukan kegagalan authentication sehingga tidak memakainya.
    challenge = True

    def __init__(self, log_message: str | None = None) -> None:
        self.log_message = log_message or type(self).__name__
        super().__init__(self.log_message)


class InvalidCredentialsError(AuthDomainError):
    """Kredensial tidak valid: email tidak terdaftar atau password tidak cocok."""


class InactiveUserError(AuthDomainError):
    """User ada, tetapi berstatus non-aktif sehingga tidak boleh mengakses aplikasi."""


class InvalidTokenError(AuthDomainError):
    """Access token tidak ada, tidak valid, kedaluwarsa, atau tidak dapat dipakai."""


class AuthorizationError(AuthDomainError):
    """User terautentikasi, tetapi role-nya tidak diizinkan menjalankan operation.

    Berbeda dari kegagalan authentication: identitas user sudah diketahui, jadi
    status yang tepat adalah 403 (bukan 401) dan pesan publiknya menyatakan
    akses ditolak. Pesan publik **tidak** mengungkap role apa yang dibutuhkan
    maupun role user tersebut; detail itu hanya dicatat server-side.
    """

    error_code = "AUTHORIZATION_DENIED"
    status_code = 403
    public_message = "Akses ditolak."
    challenge = False

    def __init__(
        self,
        *,
        user_id: object = None,
        user_role: UserRole | str | None = None,
        required_roles: Iterable[UserRole] = (),
    ) -> None:
        self.user_id = user_id
        self.user_role = user_role
        self.required_roles = tuple(required_roles)
        super().__init__(
            "authorization ditolak: "
            f"user {user_id} berrole {_role_value(user_role)} "
            f"tidak termasuk role yang diizinkan ({_role_values(self.required_roles)})"
        )


class AuthorizationPolicyError(ValueError):
    """Kesalahan *programming* saat mendefinisikan role policy.

    Bukan kegagalan request: error ini muncul saat wiring endpoint (misalnya
    policy tanpa role atau role yang tidak dikenal), dan karena itu **tidak**
    dipetakan ke response HTTP oleh ``src/middlewares`` — berbeda dari
    :class:`AuthorizationError` yang menghasilkan 403 ``AUTHORIZATION_DENIED``.
    """


def _role_value(role: UserRole | str | None) -> str:
    return getattr(role, "value", None) or "tanpa role"


def _role_values(roles: Iterable[UserRole]) -> str:
    values = sorted(getattr(role, "value", str(role)) for role in roles)
    return ", ".join(values) if values else "tidak ada"
