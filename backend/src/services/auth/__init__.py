"""Authentication aplikasi (BE-03.3).

Modul ini menyediakan:

- :class:`AuthService` — verifikasi kredensial, penerbitan access token, dan
  pemulihan current user;
- :mod:`src.services.auth.passwords` — hashing/verifikasi password (bcrypt);
- :mod:`src.services.auth.tokens` — penerbitan & validasi JWT;
- :class:`AuthDomainError` beserta turunannya — error domain yang dipetakan ke
  HTTP 401 oleh ``src.middlewares``.

Authentication menentukan "siapa User ini" dan tidak menentukan apakah User
boleh menjalankan sebuah operasi (itu authorization, BE-03.4).
"""

from src.services.auth.errors import (
    AuthDomainError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from src.services.auth.passwords import (
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    hash_password,
    verify_password,
)
from src.services.auth.service import AuthService
from src.services.auth.tokens import (
    create_access_token,
    decode_access_token,
    token_expiry,
)

__all__ = [
    "AuthService",
    "AuthDomainError",
    "InvalidCredentialsError",
    "InactiveUserError",
    "InvalidTokenError",
    "hash_password",
    "verify_password",
    "MIN_PASSWORD_LENGTH",
    "MAX_PASSWORD_LENGTH",
    "create_access_token",
    "decode_access_token",
    "token_expiry",
]
