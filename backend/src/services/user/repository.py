"""User Repository — satu-satunya tempat query dan mutasi tabel ``users``.

Repository hanya menjawab "bagaimana data User diambil/disimpan?", tanpa aturan
bisnis dan tanpa keputusan workflow. Operasi aplikasi (validasi lifecycle,
aktivasi/deaktivasi, dsb.) berada di :mod:`src.services.user.service`.

Repository ini juga bertanggung jawab menerjemahkan pelanggaran constraint
database menjadi error domain (:class:`DuplicateEmailError`), karena hanya layer
inilah yang mengetahui detail persistence. Unique constraint ``users.email``
menjadi otoritas penentu duplicate identity agar aman terhadap race condition —
service tidak melakukan pre-check yang bisa kalah cepat.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User as UserEntity
from src.services.user.domain import User
from src.services.user.errors import DuplicateEmailError
from src.services.user.mappers import apply_to_entity, to_domain
from src.services.user.validation import normalize_email

__all__ = ["UserRepository"]

# Kode SQLSTATE PostgreSQL untuk unique_violation.
_UNIQUE_VIOLATION_SQLSTATE = "23505"


class UserRepository:
    """Akses data User di atas ``AsyncSession`` yang di-inject dari luar.

    Seluruh operasi mengembalikan domain model, bukan entity ORM, sehingga
    pemanggil tidak perlu mengetahui struktur tabel.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user: User) -> User:
        """Simpan user baru dan kembalikan status hasil persist."""
        entity = apply_to_entity(user, UserEntity())
        self._session.add(entity)
        await self._commit_or_raise_duplicate(user.email)
        await self._session.refresh(entity)
        return to_domain(entity)

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Ambil user berdasarkan identifier; ``None`` bila tidak ada."""
        entity = await self._session.get(UserEntity, user_id)
        return to_domain(entity) if entity is not None else None

    async def find_by_email(self, email: str) -> User | None:
        """Cari user berdasarkan email (identity attribute authentication).

        Email dinormalisasi lebih dulu supaya pencarian konsisten dengan nilai
        yang disimpan (lowercase), dan mengembalikan ``None`` bila tidak ada.
        """
        statement = select(UserEntity).where(UserEntity.email == normalize_email(email))
        entity = (await self._session.execute(statement)).scalar_one_or_none()
        return to_domain(entity) if entity is not None else None

    async def update(self, user: User) -> User | None:
        """Perbarui user yang sudah dipersist; ``None`` bila barisnya tidak ada."""
        if user.id is None:
            raise ValueError("update memerlukan user yang sudah dipersist (id tidak boleh kosong)")

        entity = await self._session.get(UserEntity, user.id)
        if entity is None:
            return None

        apply_to_entity(user, entity)
        await self._commit_or_raise_duplicate(user.email)
        await self._session.refresh(entity)
        return to_domain(entity)

    async def exists_by_email(self, email: str) -> bool:
        """Cek keberadaan user berdasarkan email tanpa memuat seluruh baris."""
        statement = (
            select(UserEntity.id).where(UserEntity.email == normalize_email(email)).limit(1)
        )
        return (await self._session.execute(statement)).scalar_one_or_none() is not None

    async def _commit_or_raise_duplicate(self, email: str) -> None:
        """Commit perubahan, petakan unique violation menjadi error domain."""
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            if _is_unique_violation(exc):
                raise DuplicateEmailError(email) from exc
            raise


def _is_unique_violation(exc: IntegrityError) -> bool:
    """Apakah IntegrityError berasal dari unique constraint (bukan FK/NOT NULL)."""
    original = getattr(exc, "orig", None)
    if getattr(original, "sqlstate", None) == _UNIQUE_VIOLATION_SQLSTATE:
        return True
    if getattr(original, "pgcode", None) == _UNIQUE_VIOLATION_SQLSTATE:
        return True
    return "unique" in str(original).lower()
