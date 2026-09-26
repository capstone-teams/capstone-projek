"""Endpoint authentication (BE-03.3).

Router ini hanya menangani urusan HTTP: kontrak endpoint, dependency, dan
response DTO. Verifikasi kredensial, penerbitan token, serta pemulihan current
user berada di ``src.services.auth``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.schemas.auth import (
    AuthenticatedUser,
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
)
from src.services.auth.service import AuthService
from src.services.dependencies import get_auth_service, get_current_user
from src.services.user.domain import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Verifikasi kredensial dan terbitkan access token.

    Role pada authentication state berasal dari record User — client tidak dapat
    menentukan role-nya sendiri. Kegagalan authentication menghasilkan
    401 ``AUTHENTICATION_FAILED`` dengan pesan publik yang seragam.
    """
    user = await service.authenticate(username=payload.username, password=payload.password)
    access_token = await service.issue_access_token(user)

    return LoginResponse(
        access_token=access_token,
        user=AuthenticatedUser(id=user.id, role=user.role),
    )


@router.get("/me", response_model=CurrentUserResponse)
async def read_current_user(current_user: User = Depends(get_current_user)) -> CurrentUserResponse:
    """Kembalikan user yang sedang terautentikasi.

    Membutuhkan header ``Authorization: Bearer <access_token>``; role yang
    dikembalikan selalu dibaca dari record User.
    """
    return CurrentUserResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
    )
