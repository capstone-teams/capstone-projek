"""User Service — entry point operasi aplikasi terhadap User (BE-03.2).

Service ini menjawab "operasi apa yang boleh dilakukan terhadap User?", bukan
"bagaimana identitas dibuktikan?" (itu authentication, BE-03.3) dan bukan
"bagaimana data disimpan?" (itu :class:`~src.services.user.repository.UserRepository`).

Pemakaian oleh authentication (BE-03.3) cukup dengan menyediakan session:
``UserService.from_session(session)`` — tanpa perlu menyentuh database langsung.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.user.domain import User
from src.services.user.enums import UserRole
from src.services.user.errors import UserNotFoundError, UserValidationError
from src.services.user.repository import UserRepository
from src.services.user.validation import normalize_identifier

__all__ = ["UNSET", "UserService"]


class _Unset:
    """Penanda "argumen tidak diberikan" untuk update parsial.

    Dibedakan dari ``None`` supaya ``password_hash=None`` (menghapus credential)
    tetap dapat dibedakan dari "tidak diubah".
    """

    def __repr__(self) -> str:  # pragma: no cover - bantuan debug
        return "UNSET"


UNSET: Any = _Unset()


class UserService:
    """Operasi aplikasi terhadap User (create, lookup, update, lifecycle)."""

    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    @classmethod
    def from_session(cls, session: AsyncSession) -> "UserService":
        """Bangun service dengan repository di atas session yang diberikan."""
        return cls(UserRepository(session))

    async def create_user(
        self,
        *,
        name: str,
        email: str,
        role: UserRole | str,
        password_hash: str | None = None,
    ) -> User:
        """Buat user baru.

        Domain model divalidasi lebih dulu (identity, role, status) sebelum
        menyentuh database, sehingga data tidak valid tidak pernah dipersist.
        Email duplikat menghasilkan :class:`DuplicateEmailError`.
        """
        user = User.create(name=name, email=email, role=role, password_hash=password_hash)
        return await self._repository.create(user)

    async def find_user_by_id(self, user_id: uuid.UUID | str) -> User | None:
        """Cari user berdasarkan identifier; ``None`` bila tidak ditemukan."""
        return await self._repository.get_by_id(_as_identifier(user_id))

    async def get_user(self, user_id: uuid.UUID | str) -> User:
        """Ambil user berdasarkan identifier atau lempar :class:`UserNotFoundError`."""
        return _require_found(await self.find_user_by_id(user_id), user_id)

    async def find_user_by_email(self, email: str) -> User | None:
        """Cari user berdasarkan email; ``None`` bila tidak ditemukan."""
        return await self._repository.find_by_email(email)

    async def get_user_by_email(self, email: str) -> User:
        """Ambil user berdasarkan email atau lempar :class:`UserNotFoundError`."""
        return _require_found(await self.find_user_by_email(email), email)

    async def update_user(
        self,
        user_id: uuid.UUID | str,
        *,
        name: Any = UNSET,
        email: Any = UNSET,
        role: Any = UNSET,
        password_hash: Any = UNSET,
    ) -> User:
        """Perbarui atribut user yang diberikan (argumen lain dibiarkan apa adanya).

        Perubahan tetap melewati validasi domain sebelum dipersist, dan email
        duplikat menghasilkan :class:`DuplicateEmailError`.
        """
        current = await self.get_user(user_id)
        changes = {
            field: value
            for field, value in (
                ("name", name),
                ("email", email),
                ("role", role),
                ("password_hash", password_hash),
            )
            if value is not UNSET
        }

        updated = replace(current, **changes)
        return await self._persist(updated)

    async def activate_user(self, user_id: uuid.UUID | str) -> User:
        """Aktifkan user sehingga boleh mengakses aplikasi."""
        user = await self.get_user(user_id)
        user.activate()
        return await self._persist(user)

    async def deactivate_user(self, user_id: uuid.UUID | str) -> User:
        """Nonaktifkan user (deaktivasi, bukan penghapusan permanen)."""
        user = await self.get_user(user_id)
        user.deactivate()
        return await self._persist(user)

    async def get_user_role(self, user_id: uuid.UUID | str) -> UserRole:
        """Role user, dibaca dari record User (bukan dari input client)."""
        return (await self.get_user(user_id)).role

    async def is_email_registered(self, email: str) -> bool:
        """Existence check berdasarkan email, dipakai authentication/feature lain."""
        return await self._repository.exists_by_email(email)

    async def list_users(self) -> list[User]:
        """Daftar seluruh user, diurutkan berdasarkan email.

        Dipakai operation yang memang membutuhkan seluruh user (contoh: daftar
        user untuk ADMIN pada BE-03.4).
        """
        return await self._repository.list_all()

    async def _persist(self, user: User) -> User:
        """Simpan perubahan user; baris yang hilang di tengah jalan tetap not-found."""
        persisted = await self._repository.update(user)
        if persisted is None:
            raise UserNotFoundError(user.id)
        return persisted


def _as_identifier(user_id: uuid.UUID | str) -> uuid.UUID:
    identifier = normalize_identifier(user_id)
    if identifier is None:
        raise UserValidationError("id", "identifier user wajib diisi")
    return identifier


def _require_found(user: User | None, identifier: object) -> User:
    if user is None:
        raise UserNotFoundError(identifier)
    return user
