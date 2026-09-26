"""Error authentication (BE-03.3).

Authentication menjawab "siapa User ini?". Kegagalan authentication dipetakan
oleh ``src/middlewares`` ke HTTP 401 dengan kode ``AUTHENTICATION_FAILED``
(lihat ``docs/02. design/design-api.md``).

Pesan publik sengaja **identik** untuk seluruh penyebab kegagalan — email tidak
terdaftar, password salah, user tidak aktif, maupun user tanpa credential
lokal — supaya response tidak dapat dipakai melakukan *user enumeration*.
Detail penyebab tetap dicatat server-side melalui ``log_message``.
"""

from __future__ import annotations


class AuthDomainError(Exception):
    """Base error authentication/authorization."""

    error_code = "AUTHENTICATION_FAILED"
    status_code = 401
    public_message = "Autentikasi gagal."

    def __init__(self, log_message: str | None = None) -> None:
        self.log_message = log_message or type(self).__name__
        super().__init__(self.log_message)


class InvalidCredentialsError(AuthDomainError):
    """Kredensial tidak valid: email tidak terdaftar atau password tidak cocok."""


class InactiveUserError(AuthDomainError):
    """User ada, tetapi berstatus non-aktif sehingga tidak boleh mengakses aplikasi."""


class InvalidTokenError(AuthDomainError):
    """Access token tidak ada, tidak valid, kedaluwarsa, atau tidak dapat dipakai."""
