"""Entity User (BE-02).

Kolom mengikuti atribut user Moodle (``core_user_create_users``): ``username``,
``firstname``, ``lastname``, ``email``, dan ``password``. Dengan bentuk yang
sama, sinkronisasi user ke Moodle tidak memerlukan tabel pemetaan tersendiri —
perbedaannya hanya pada nilai ID lokal (ShortUUID).

Dua hal yang perlu diperhatikan:

- ``password`` menyimpan **hash** bcrypt dari ``src.services.auth.passwords``,
  bukan password mentah. Password mentah hanya ada saat Moodle membuat user
  (parameter API Moodle) dan tidak pernah disimpan di sini.
- ``username`` adalah atribut Moodle. Login aplikasi tetap memakai ``email``
  sebagai identity attribute (lihat ``backend/README.md``).

Nilai role/status didefinisikan di sini karena sekaligus menjadi tipe kolom
database (native enum PostgreSQL ``userrole``/``userstatus``) dan menjadi sumber
tunggal nilainya untuk layer domain (lihat ``src.services.user.enums``).
"""

import enum

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class UserRole(str, enum.Enum):
    INSTRUCTOR = "INSTRUCTOR"
    STUDENT = "STUDENT"
    ADMIN = "ADMIN"


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class User(BaseModel):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    firstname: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    lastname: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    # Hash bcrypt (kolom ``String(255)`` mengikuti panjang hash yang dihasilkan);
    # ``NULL`` berarti user tidak memiliki credential lokal.
    password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        nullable=False,
    )

    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus),
        nullable=False,
    )
