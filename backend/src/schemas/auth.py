"""DTO authentication (BE-03.3).

Kontrak HTTP mengikuti ``docs/02. design/design-api.md`` §5 (login & current
user). Response tidak pernah memuat password, password hash, token lain, maupun
atribut credential apa pun.

Catatan import: enum role diambil dari :mod:`src.services.user.enums` — sumber
tunggal nilai role/status — supaya schema tidak mendefinisikan ulang nilai role
(bandingkan BE-03.1). Modul ini tetap bebas SQLAlchemy dan bebas logika domain.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.services.auth.passwords import MAX_PASSWORD_LENGTH
from src.services.user.enums import UserRole
from src.services.user.validation import MAX_EMAIL_LENGTH

__all__ = [
    "AuthenticatedUser",
    "CurrentUserResponse",
    "LoginRequest",
    "LoginResponse",
]


class LoginRequest(BaseModel):
    """Body ``POST /api/v1/auth/login``.

    Field ``username`` mengikuti kontrak API (design-api §5.1) dan **berisi
    email** user, karena email adalah identity attribute untuk login aplikasi.
    Ini bukan kolom ``users.username`` (username Moodle) — nilai username tidak
    pernah dipakai untuk login lokal.
    """

    model_config = ConfigDict(
        json_schema_extra={"example": {"username": "dosen@itk.ac.id", "password": "rahasia123"}}
    )

    username: str = Field(min_length=1, max_length=MAX_EMAIL_LENGTH)
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)


class AuthenticatedUser(BaseModel):
    """Identitas user minimum pada response login (design-api §5.1)."""

    id: str
    role: UserRole


class LoginResponse(BaseModel):
    """Response login: authentication state untuk request berikutnya."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: AuthenticatedUser


class CurrentUserResponse(BaseModel):
    """Response ``GET /api/v1/auth/me`` (design-api §5.2).

    Field identity mengikuti atribut user Moodle (``username``, ``firstname``,
    ``lastname``, ``email``); credential tidak pernah ikut dikembalikan.
    """

    id: str
    username: str
    firstname: str
    lastname: str
    email: str
    role: UserRole
