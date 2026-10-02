"""Access token (JWT) untuk authentication state (BE-03.3).

Token hanya membawa identifier user (``sub``) beserta ``iat``/``exp``. Role
**tidak** dijadikan klaim tepercaya: role dan status selalu dibaca ulang dari
record User pada setiap request (lihat ``AuthService.get_authenticated_user``),
sehingga perubahan role atau deaktivasi langsung berlaku dan client tidak dapat
menentukan role-nya sendiri.

Konfigurasi (``SECRET_KEY``, ``JWT_ALGORITHM``, ``ACCESS_TOKEN_EXPIRE_MINUTES``)
dibaca dari environment configuration, bukan dari kode.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from src.config.settings import settings
from src.services.auth.errors import InvalidTokenError

__all__ = [
    "MIN_SECRET_KEY_LENGTH",
    "create_access_token",
    "decode_access_token",
    "token_expiry",
    "warn_if_secret_is_weak",
]

logger = logging.getLogger(__name__)

# Panjang minimum SECRET_KEY yang dianggap layak untuk menandatangani token.
MIN_SECRET_KEY_LENGTH = 32

_REQUIRED_CLAIMS = ["exp", "sub"]


def token_expiry() -> timedelta:
    """Masa berlaku access token sesuai konfigurasi aplikasi."""
    return timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)


def create_access_token(
    subject: uuid.UUID,
    *,
    expires_delta: timedelta | None = None,
    issued_at: datetime | None = None,
) -> str:
    """Terbitkan access token bertanda tangan untuk ``subject`` (identifier user)."""
    issued = issued_at or datetime.now(timezone.utc)
    expires = issued + (expires_delta if expires_delta is not None else token_expiry())

    payload = {
        "sub": str(subject),
        "iat": int(issued.timestamp()),
        "exp": int(expires.timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID:
    """Ambil identifier user dari token; lempar :class:`InvalidTokenError` bila tidak valid.

    Signature, masa berlaku (``exp``), dan kelengkapan klaim wajib diverifikasi
    oleh PyJWT; kegagalan apa pun dipetakan ke satu error domain.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": _REQUIRED_CLAIMS},
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(f"token ditolak: {type(exc).__name__}") from exc

    try:
        return uuid.UUID(str(payload["sub"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidTokenError("token ditolak: sub bukan identifier yang valid") from exc


def warn_if_secret_is_weak() -> None:
    """Catat peringatan bila SECRET_KEY terlalu pendek untuk menandatangani token.

    Nilai secret tidak pernah ditulis ke log; hanya panjangnya yang disebutkan.
    Dijalankan saat startup supaya konfigurasi yang tidak aman terlihat tanpa
    membuat aplikasi gagal berjalan di lingkungan development.
    """
    if len(settings.SECRET_KEY) < MIN_SECRET_KEY_LENGTH:
        logger.warning(
            "SECRET_KEY hanya %d karakter (minimum yang disarankan %d): token dapat "
            "dipalsukan. Set nilai kuat pada environment configuration.",
            len(settings.SECRET_KEY),
            MIN_SECRET_KEY_LENGTH,
        )
