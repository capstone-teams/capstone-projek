"""DTO authentication (BE-03.3).

Kontrak HTTP mengikuti ``docs/02. design/design-api.md`` §5 (login & current
user). Response tidak pernah memuat password, password hash, token lain, maupun
atribut credential apa pun.

Dokumentasi integrasi untuk frontend — request/response, masa berlaku token,
perilaku token kedaluwarsa, role, dan daftar error — berada di
``docs/02. design/auth-api-integration.md`` (BE-06.1). Deskripsi pada field di
modul ini menjadi sumber OpenAPI, sehingga Swagger UI menampilkan kontrak yang
sama.

Catatan import: enum role diambil dari :mod:`src.services.user.enums` — sumber
tunggal nilai role/status — supaya schema tidak mendefinisikan ulang nilai role
(bandingkan BE-03.1). Modul ini tetap bebas SQLAlchemy dan bebas logika domain.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.services.auth.passwords import MAX_PASSWORD_LENGTH
from src.services.user.enums import UserRole
from src.services.user.validation import MAX_EMAIL_LENGTH, MAX_USERNAME_LENGTH

__all__ = [
    "AuthenticatedUser",
    "CurrentUserResponse",
    "LoginRequest",
    "LoginResponse",
]

# Field login menerima username atau email; batas panjangnya mengikuti yang
# terpanjang agar nilai valid untuk salah satu bentuk tidak ditolak schema.
MAX_LOGIN_IDENTIFIER_LENGTH = max(MAX_EMAIL_LENGTH, MAX_USERNAME_LENGTH)

# Contoh token palsu untuk dokumentasi. Nilainya bukan token yang dapat dipakai:
# signature-nya tidak valid, sehingga tidak pernah menjadi credential di repo.
EXAMPLE_ACCESS_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiJkZW1vVXNlcklkMjJLYXJha3RlciIsImlhdCI6MTcwMDAwMDAwMCwiZXhwIjoxNzAwMDAxODAwfQ"
    ".contoh-signature-tidak-valid"
)


class LoginRequest(BaseModel):
    """Body ``POST /api/v1/auth/login``.

    Field ``username`` mengikuti kontrak API (design-api §5.1) dan berisi
    **identifier login**: username (kolom ``users.username``, atribut Moodle)
    atau email user. Keduanya menunjuk ke record User yang sama dan password
    tetap diverifikasi terhadap credential lokal. Password akun uji berasal dari
    kanal internal tim (BE-06.3), bukan dari repository.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "dosen.demo@itk.ac.id",
                "password": "ContohPasswordUji",
            }
        }
    )

    username: str = Field(
        min_length=1,
        max_length=MAX_LOGIN_IDENTIFIER_LENGTH,
        description=(
            "Username atau email user. Email tidak membedakan kapitalisasi; "
            "username dicocokkan persis lebih dulu."
        ),
        examples=["dosen.demo@itk.ac.id", "dosen.demo"],
    )
    password: str = Field(
        min_length=1,
        max_length=MAX_PASSWORD_LENGTH,
        description="Password akun. Nilai tidak pernah dikembalikan oleh API.",
        examples=["ContohPasswordUji"],
    )


class AuthenticatedUser(BaseModel):
    """Identitas user minimum pada response login (design-api §5.1)."""

    id: str = Field(
        description="Identifier user (ShortUUID 22 karakter).",
        examples=["kY3vQ9mN2pLxR7tWzA5bcd"],
    )
    role: UserRole = Field(
        description=(
            "Role kanonik dari record User: ``INSTRUCTOR``, ``STUDENT``, atau "
            "``ADMIN``. Role tidak berasal dari client dan tidak menjadi klaim token."
        ),
        examples=["INSTRUCTOR"],
    )


class LoginResponse(BaseModel):
    """Response login: authentication state untuk request berikutnya."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": EXAMPLE_ACCESS_TOKEN,
                "token_type": "bearer",
                "user": {"id": "kY3vQ9mN2pLxR7tWzA5bcd", "role": "INSTRUCTOR"},
            }
        }
    )

    access_token: str = Field(
        description=(
            "JWT bertanda tangan (``HS256``) dengan klaim ``sub``, ``iat``, dan "
            "``exp``. Kirim pada request berikutnya sebagai header "
            "``Authorization: Bearer <access_token>``. Masa berlaku mengikuti "
            "``ACCESS_TOKEN_EXPIRE_MINUTES`` (default 30 menit); setelah "
            "kedaluwarsa semua endpoint terproteksi menjawab 401."
        ),
        examples=[EXAMPLE_ACCESS_TOKEN],
    )
    token_type: Literal["bearer"] = Field(
        default="bearer",
        description="Skema autentikasi; selalu ``bearer``.",
        examples=["bearer"],
    )
    user: AuthenticatedUser


class CurrentUserResponse(BaseModel):
    """Response ``GET /api/v1/auth/me`` (design-api §5.2).

    Field identity mengikuti atribut user Moodle (``username``, ``firstname``,
    ``lastname``, ``email``); credential tidak pernah ikut dikembalikan.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "kY3vQ9mN2pLxR7tWzA5bcd",
                "username": "dosen.demo",
                "firstname": "Dosen",
                "lastname": "Demo",
                "email": "dosen.demo@itk.ac.id",
                "role": "INSTRUCTOR",
            }
        }
    )

    id: str = Field(
        description="Identifier user (ShortUUID 22 karakter).",
        examples=["kY3vQ9mN2pLxR7tWzA5bcd"],
    )
    username: str = Field(
        description="Atribut username Moodle; juga dapat dipakai sebagai identifier login.",
        examples=["dosen.demo"],
    )
    firstname: str = Field(description="Nama depan.", examples=["Dosen"])
    lastname: str = Field(description="Nama belakang.", examples=["Demo"])
    email: str = Field(
        description="Email user (lowercase); juga dapat dipakai sebagai identifier login.",
        examples=["dosen.demo@itk.ac.id"],
    )
    role: UserRole = Field(
        description=(
            "Role kanonik dari record User: ``INSTRUCTOR``, ``STUDENT``, atau "
            "``ADMIN``. Dibaca ulang dari database pada setiap request."
        ),
        examples=["INSTRUCTOR"],
    )
