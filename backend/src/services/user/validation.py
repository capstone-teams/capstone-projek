"""Validasi dan normalisasi identity field User.

Seluruh fungsi di sini murni: tanpa I/O, tanpa database, dan tanpa framework
HTTP, sehingga aturan identity dapat diuji tanpa infrastruktur apa pun.

Batas panjang mengikuti tipe kolom pada ``src.models.user`` (``String(255)``),
supaya nilai yang lolos validasi domain tidak ditolak oleh database.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from src.services.user.enums import UserRole, UserStatus
from src.services.user.errors import UserValidationError

MAX_NAME_LENGTH = 255
MAX_EMAIL_LENGTH = 255
MAX_PASSWORD_HASH_LENGTH = 255

# Local part: atom dipisah titik, sehingga titik di awal/akhir atau berurutan
# (``.a@x.com``, ``a.@x.com``, ``a..b@x.com``) ditolak.
# Domain: label alfanumerik (dash hanya di tengah) diakhiri TLD alfabetik.
_EMAIL_PATTERN = re.compile(
    r"^(?P<local>[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*)"
    r"@"
    r"(?P<domain>(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63})$"
)


def normalize_name(value: object) -> str:
    """Validasi display name dan buang spasi di tepi.

    Empty name tidak bermakna di domain ini: endpoint ``/auth/me`` menampilkan
    name, sehingga name wajib terisi.
    """
    if not isinstance(value, str):
        raise UserValidationError("name", "harus berupa teks")

    name = value.strip()
    if not name:
        raise UserValidationError("name", "tidak boleh kosong atau hanya spasi")
    if any(not char.isprintable() for char in name):
        raise UserValidationError("name", "tidak boleh mengandung karakter kontrol")
    if len(name) > MAX_NAME_LENGTH:
        raise UserValidationError(
            "name", f"maksimal {MAX_NAME_LENGTH} karakter"
        )
    return name


def normalize_email(value: object) -> str:
    """Validasi email dan normalisasi ke huruf kecil.

    Email adalah unique identity attribute (``users.email`` UNIQUE). PostgreSQL
    membandingkan string secara case-sensitive, sehingga normalisasi lowercase
    di domain mencegah ``Dosen@itk.ac.id`` dan ``dosen@itk.ac.id`` menjadi dua
    user berbeda.
    """
    if not isinstance(value, str):
        raise UserValidationError("email", "harus berupa teks")

    email = value.strip().lower()
    if not email:
        raise UserValidationError("email", "tidak boleh kosong atau hanya spasi")
    if len(email) > MAX_EMAIL_LENGTH:
        raise UserValidationError(
            "email", f"maksimal {MAX_EMAIL_LENGTH} karakter"
        )
    if any(char.isspace() for char in email) or not _EMAIL_PATTERN.match(email):
        raise UserValidationError("email", f"format email tidak valid: {value!r}")
    return email


def normalize_role(value: object) -> UserRole:
    """Pastikan role hanya berisi nilai yang telah didefinisikan.

    Menerima instance :class:`UserRole` atau string nama/nilai role
    (case-insensitive) dan selalu mengembalikan enum kanonik, sehingga role
    arbitrary seperti ``"SUPERADMIN"`` tidak pernah masuk ke domain.
    """
    return _normalize_enum(value, UserRole, field="role")


def normalize_status(value: object) -> UserStatus:
    """Pastikan status hanya berisi nilai yang telah didefinisikan."""
    return _normalize_enum(value, UserStatus, field="status")


def normalize_password_hash(value: object) -> str | None:
    """Validasi password hash lokal.

    ``None`` berarti user tidak memakai local authentication. Nilai ini hanya
    relevan bila mekanisme authentication final memakai credential lokal
    (lihat catatan BE-03.1), jadi tidak ada pemaksaan password di domain.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise UserValidationError("password_hash", "harus berupa teks atau None")

    digest = value.strip()
    if not digest:
        raise UserValidationError(
            "password_hash", "tidak boleh kosong; gunakan None bila tidak memakai local authentication"
        )
    if any(char.isspace() for char in digest):
        raise UserValidationError(
            "password_hash", "harus berupa hash, bukan password mentah"
        )
    if len(digest) > MAX_PASSWORD_HASH_LENGTH:
        raise UserValidationError(
            "password_hash", f"maksimal {MAX_PASSWORD_HASH_LENGTH} karakter"
        )
    return digest


def normalize_identifier(value: object) -> uuid.UUID | None:
    """Validasi identifier User (UUID) yang belum tentu tersedia.

    ``None`` pada user yang belum dipersist, karena identifier dibentuk oleh
    database foundation (BE-02).
    """
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        try:
            return uuid.UUID(value.strip())
        except ValueError:
            raise UserValidationError("id", f"bukan UUID yang valid: {value!r}") from None
    raise UserValidationError("id", "harus berupa UUID atau None")


def normalize_timestamp(value: object, field: str) -> datetime | None:
    """Validasi metadata lifecycle (``created_at`` / ``updated_at``).

    Timestamp dikelola database (``server_default`` / ``onupdate``), sehingga
    domain hanya memvalidasi nilainya dan tidak membentuknya sendiri.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    raise UserValidationError(field, "harus berupa datetime atau None")


def _normalize_enum(value: object, enum_type: type, field: str) -> object:
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        try:
            return enum_type(value.strip().upper())
        except ValueError:
            pass

    valid_values = ", ".join(member.value for member in enum_type)
    raise UserValidationError(
        field, f"nilai tidak dikenal: {value!r}; nilai valid: {valid_values}"
    )
