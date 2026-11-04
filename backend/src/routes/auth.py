"""Endpoint authentication (BE-03.3).

Router ini hanya menangani urusan HTTP: kontrak endpoint, dependency, dan
response DTO. Verifikasi kredensial, penerbitan token, serta pemulihan current
user berada di ``src.services.auth``.

Field ``username`` pada body login berisi identifier login — username atau email
user (kontrak API design-api §5.1) — lihat
:class:`src.schemas.auth.LoginRequest`.

Dokumentasi OpenAPI (BE-06.1): setiap endpoint menyertakan contoh request,
response sukses, dan response gagal. Panduan integrasi lengkap — format token,
masa berlaku, perilaku kedaluwarsa, matriks role, dan daftar kode error — berada
di ``docs/02. design/auth-api-integration.md``.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, status

from src.schemas.auth import (
    AuthenticatedUser,
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
)
from src.schemas.errors import ErrorResponse
from src.services.auth.service import AuthService
from src.services.dependencies import get_auth_service, get_current_user
from src.services.user.domain import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Contoh mengikuti amplop error design-api §18. Nilainya sama dengan response
# yang benar-benar dikembalikan handler, sehingga "Try it out" di Swagger UI
# memperlihatkan kontrak yang dapat dicocokkan dengan hasil sebenarnya.
AUTHENTICATION_FAILED_EXAMPLE = {
    "error": {
        "code": "AUTHENTICATION_FAILED",
        "message": "Autentikasi gagal.",
        "details": [],
    }
}

VALIDATION_FAILED_EXAMPLE = {
    "error": {
        "code": "VALIDATION_FAILED",
        "message": "Data request tidak valid.",
        "details": [{"field": "password", "message": "Field required"}],
    }
}

UNAUTHORIZED_RESPONSE = {
    "model": ErrorResponse,
    "description": (
        "Autentikasi gagal; pesan publiknya seragam agar response tidak dapat "
        "dipakai untuk *user enumeration*. Response menyertakan header "
        "`WWW-Authenticate: Bearer`."
    ),
    "headers": {
        "WWW-Authenticate": {
            "description": "Challenge autentikasi Bearer.",
            "schema": {"type": "string", "example": "Bearer"},
        }
    },
    "content": {"application/json": {"example": AUTHENTICATION_FAILED_EXAMPLE}},
}

LOGIN_UNAUTHORIZED_RESPONSE = {
    **UNAUTHORIZED_RESPONSE,
    "description": (
        "Identifier tidak terdaftar, password salah, user non-aktif, atau user "
        "tanpa credential lokal. Semua penyebab memakai pesan publik yang sama. "
        "Response menyertakan header `WWW-Authenticate: Bearer`."
    ),
}

TOKEN_UNAUTHORIZED_RESPONSE = {
    **UNAUTHORIZED_RESPONSE,
    "description": (
        "Header `Authorization` tidak ada atau bukan skema Bearer, token tidak "
        "valid/kedaluwarsa, atau user sudah non-aktif. Response menyertakan header "
        "`WWW-Authenticate: Bearer`; client harus menghapus token dan login ulang."
    ),
}

VALIDATION_FAILED_RESPONSE = {
    "model": ErrorResponse,
    "description": (
        "Body request tidak memenuhi schema (mis. field wajib tidak ada atau "
        "password kosong). Format mengikuti design-api §18; nilai input tidak "
        "pernah dikembalikan."
    ),
    "content": {"application/json": {"example": VALIDATION_FAILED_EXAMPLE}},
}


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login dan terbitkan access token",
    responses={401: LOGIN_UNAUTHORIZED_RESPONSE, 422: VALIDATION_FAILED_RESPONSE},
)
async def login(
    payload: LoginRequest = Body(
        ...,
        openapi_examples={
            "email": {
                "summary": "Login dengan email",
                "description": (
                    "Field `username` berisi email akun. Password akun uji berasal "
                    "dari kanal internal tim (BE-06.3), bukan repository."
                ),
                "value": {
                    "username": "dosen.demo@itk.ac.id",
                    "password": "ContohPasswordUji",
                },
            },
            "username": {
                "summary": "Login dengan username",
                "description": "Field `username` berisi username Moodle akun.",
                "value": {"username": "dosen.demo", "password": "ContohPasswordUji"},
            },
        },
    ),
    service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Verifikasi kredensial dan terbitkan access token.

    `username` boleh berisi **username atau email** user. Role pada authentication
    state berasal dari record User — client tidak dapat menentukan role-nya
    sendiri. Response sukses berisi JWT beserta identitas minimum user.

    Kegagalan authentication (identifier tidak terdaftar, password salah, user
    non-aktif, atau user tanpa credential lokal) selalu menghasilkan
    **401 `AUTHENTICATION_FAILED`** dengan pesan publik yang seragam, sehingga
    response tidak dapat dipakai untuk *user enumeration*.
    """
    user = await service.authenticate(identifier=payload.username, password=payload.password)
    access_token = await service.issue_access_token(user)

    return LoginResponse(
        access_token=access_token,
        user=AuthenticatedUser(id=user.id, role=user.role),
    )


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Ambil current user",
    responses={401: TOKEN_UNAUTHORIZED_RESPONSE},
)
async def read_current_user(current_user: User = Depends(get_current_user)) -> CurrentUserResponse:
    """Kembalikan user yang sedang terautentikasi.

    Membutuhkan header `Authorization: Bearer <access_token>` yang diperoleh dari
    `POST /api/v1/auth/login`. Role dan status dibaca ulang dari record User pada
    setiap request, sehingga perubahan role atau deaktivasi langsung berlaku.

    Token yang tidak ada, tidak valid, atau kedaluwarsa menghasilkan **401
    `AUTHENTICATION_FAILED`** dengan header `WWW-Authenticate: Bearer`. Tidak ada
    endpoint refresh/logout: client menghapus token saat logout.
    """
    return CurrentUserResponse(
        id=current_user.id,
        username=current_user.username,
        firstname=current_user.firstname,
        lastname=current_user.lastname,
        email=current_user.email,
        role=current_user.role,
    )
