"""Base declarative dan abstract ``BaseModel`` untuk seluruh entity ORM (BE-02).

Identifier seluruh entity memakai **ShortUUID** — representasi base57 dari UUID
(22 karakter, tanpa karakter ambigu seperti ``0``/``O``/``I``/``l``) — sehingga
ID aman ditampilkan pada URL/UI tanpa encoding tambahan, sementara nilainya
tetap acak (bukan berurutan seperti auto-increment).

``created_at`` dan ``updated_at`` dikelola database (``server_default`` /
``onupdate``), bukan oleh aplikasi, agar satu sumber waktu berlaku untuk semua
penulis data.
"""

from datetime import datetime

import shortuuid
from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

__all__ = ["ID_LENGTH", "Base", "BaseModel"]

# Panjang identifier ShortUUID. Dipakai sebagai panjang kolom ``id`` dan
# diverifikasi ulang oleh domain (lihat ``src.services.user.validation``).
ID_LENGTH = 22


class Base(DeclarativeBase):
    """Declarative base SQLAlchemy; pemilik ``metadata`` seluruh entity."""


class BaseModel(Base):
    """Kolom yang dimiliki seluruh entity: identifier dan timestamp lifecycle."""

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(ID_LENGTH),
        primary_key=True,
        default=shortuuid.uuid,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Nama constraint sama pada setiap tabel (nama constraint hanya perlu unik
    # per tabel), sehingga pemeriksaan panjang identifier tidak bisa dilewati.
    __table_args__ = (
        CheckConstraint(f"length(id) = {ID_LENGTH}", name="ck_id_length"),
    )
