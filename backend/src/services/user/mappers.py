"""Pemetaan antara entity ORM (BE-02) dan domain model (BE-03.1).

Pemetaan berada di layer service supaya domain tetap bebas SQLAlchemy, dan
repository tetap menjadi satu-satunya tempat yang menyentuh entity persistence.

Catatan: domain hanya dipetakan dari entity yang sudah dipersist (punya id dan
timestamp). ``apply_to_entity`` dipakai untuk insert maupun update sehingga
aturan penulisan kolom hanya didefinisikan di satu tempat.
"""

from __future__ import annotations

from src.models.user import User as UserEntity
from src.services.user.domain import User

__all__ = ["apply_to_entity", "to_domain"]


def to_domain(entity: UserEntity) -> User:
    """Bangun domain :class:`User` dari baris tabel ``users``.

    Nilai dari database tetap melewati validasi domain, sehingga invariant
    (email lowercase, role/status kanonik) tetap berlaku untuk data yang dibaca.
    """
    return User(
        id=entity.id,
        name=entity.name,
        email=entity.email,
        role=entity.role,
        status=entity.status,
        password_hash=entity.password_hash,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def apply_to_entity(user: User, entity: UserEntity) -> UserEntity:
    """Salin nilai domain ke entity ORM (insert atau update).

    ``id`` hanya disalin bila domain sudah punya identifier; user baru
    membiarkan kolom ``id`` dibentuk oleh database foundation.
    """
    if user.id is not None:
        entity.id = user.id
    entity.name = user.name
    entity.email = user.email
    entity.role = user.role
    entity.status = user.status
    entity.password_hash = user.password_hash
    return entity
