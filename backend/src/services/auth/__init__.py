"""Authentication (BE-03.3) dan authorization (BE-03.4) aplikasi.

Modul ini menyediakan:

- :class:`AuthService` — verifikasi kredensial, penerbitan access token, dan
  pemulihan current user;
- :class:`RolePolicy` (:mod:`src.services.auth.authorization`) — keputusan
  allow/deny berbasis role dari record User, dipakai ulang endpoint melalui
  :func:`src.services.dependencies.require_roles`;
- :mod:`src.services.auth.passwords` — hashing/verifikasi password (bcrypt);
- :mod:`src.services.auth.tokens` — penerbitan & validasi JWT;
- :class:`AuthDomainError` beserta turunannya — error domain yang dipetakan ke
  HTTP 401 ``AUTHENTICATION_FAILED`` maupun 403 ``AUTHORIZATION_DENIED`` oleh
  ``src.middlewares``.

Authentication menentukan "siapa User ini"; apakah User boleh menjalankan
sebuah operasi ditentukan authorization, dan keduanya dipisah sehingga
kegagalan authorization bukan kegagalan authentication (401 vs 403).
"""

from src.services.auth.authorization import RolePolicy
from src.services.auth.errors import (
    AuthDomainError,
    AuthorizationError,
    AuthorizationPolicyError,
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
    "AuthorizationError",
    "AuthorizationPolicyError",
    "InvalidCredentialsError",
    "InactiveUserError",
    "InvalidTokenError",
    "RolePolicy",
    "hash_password",
    "verify_password",
    "MIN_PASSWORD_LENGTH",
    "MAX_PASSWORD_LENGTH",
    "create_access_token",
    "decode_access_token",
    "token_expiry",
]
