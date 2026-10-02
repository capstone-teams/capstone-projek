"""Endpoint administrasi (BE-03.4).

Router ini adalah contoh nyata pemakaian role authorization: keputusan
boleh/tidaknya sebuah operation berada di
:mod:`src.services.auth.authorization`, sedangkan router hanya menempelkan
dependency :func:`src.services.dependencies.require_roles` dan memetakan hasil
service ke DTO. Tidak ada pengecekan role yang ditulis manual di sini.

Seluruh endpoint di router ini memakai satu policy (``admin_only``) yang sama,
sehingga guard dapat dipakai ulang antar endpoint tanpa duplikasi logic.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from src.schemas.admin import AdminUserListResponse, AdminUserResponse
from src.services.dependencies import get_user_service, require_roles
from src.services.user.domain import User
from src.services.user.enums import UserRole
from src.services.user.service import UserService

router = APIRouter(prefix="/admin", tags=["Administration"])

# Policy ADMIN-only, didefinisikan sekali dan dipakai ulang oleh seluruh endpoint
# pada router ini (maupun router lain yang membutuhkannya).
admin_only = require_roles(UserRole.ADMIN)


def _to_response(user: User) -> AdminUserResponse:
    """Petakan domain User ke DTO administrasi (tanpa atribut credential)."""
    return AdminUserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
    )


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    _admin: User = Depends(admin_only),
    service: UserService = Depends(get_user_service),
) -> AdminUserListResponse:
    """Daftar seluruh user, diurutkan berdasarkan email.

    Hanya ADMIN yang boleh lewat; user terautentikasi dengan role lain
    mendapat 403 ``AUTHORIZATION_DENIED``, dan request tanpa authentication
    berhenti di 401 ``AUTHENTICATION_FAILED``.
    """
    users = await service.list_users()
    return AdminUserListResponse(users=[_to_response(user) for user in users])


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: uuid.UUID,
    _admin: User = Depends(admin_only),
    service: UserService = Depends(get_user_service),
) -> AdminUserResponse:
    """Detail satu user; 404 ``RESOURCE_NOT_FOUND`` bila tidak ada."""
    return _to_response(await service.get_user(user_id))
