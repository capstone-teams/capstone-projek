"""DTO operasi administrasi (BE-03.4).

Response administrasi hanya memuat atribut yang memang dibutuhkan pemanggil.
``password`` (hash credential) tidak pernah ada di sini: credential tidak boleh
dikembalikan melalui API (design-api §23), termasuk pada operasi yang hanya
boleh dijalankan ADMIN.

Field identity mengikuti atribut user Moodle (``username``, ``firstname``,
``lastname``, ``email``). Enum role/status diambil dari
:mod:`src.services.user.enums` — sumber tunggal nilai role/status — sehingga
schema tidak mendefinisikan ulang nilainya.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from src.services.user.enums import UserRole, UserStatus

__all__ = ["AdminUserResponse", "AdminUserListResponse"]


class AdminUserResponse(BaseModel):
    """Representasi satu user untuk pemanggil yang sudah diotorisasi ADMIN."""

    id: str
    username: str
    firstname: str
    lastname: str
    email: str
    role: UserRole
    status: UserStatus
    created_at: datetime | None = None


class AdminUserListResponse(BaseModel):
    """Daftar user pada ``GET /api/v1/admin/users``."""

    users: list[AdminUserResponse]
