"""Validasi dan normalisasi identity field User.

Seluruh fungsi di sini murni: tanpa I/O, tanpa database, dan tanpa framework
HTTP, sehingga aturan identity dapat diuji tanpa infrastruktur apa pun.

Nama field mengikuti atribut user Moodle — ``username``, ``firstname``,
``lastname``, ``email``, ``password`` — dan batas panjangnya mengikuti tipe
kolom pada ``src.models.user`` (``String(255)``), supaya nilai yang lolos
validasi domain tidak ditolak oleh database.
"""

from __future__ import annotations

import re
from datetime import datetime

from src.models.base import ID_LENGTH
from src.services.user.enums import UserRole, UserStatus
from src.services.user.errors import UserValidationError

MAX_USERNAME_LENGTH = 255
MAX_FIRSTNAME_LENGTH = 255
MAX_LASTNAME_LENGTH = 255
MAX_EMAIL_LENGTH = 255
MAX_PASSWORD_HASH_LENGTH = 255

# Alfabet default ShortUUID (base57): huruf/angka yang tidak mudah tertukar
# (``0``/``O``/``I``/``l``/``1`` tidak dipakai). Panjang identifier mengikuti
# ``src.models.base.ID_LENGTH`` agar domain dan kolom database tidak menyimpang.
SHORTUUID_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

# Pola identifier ShortUUID. Dipakai untuk memvalidasi nilai domain dan juga oleh
# layer HTTP (path parameter) supaya request cacat berhenti sebagai 422, bukan
# sampai ke service/query database.
SHORTUUID_PATTERN = rf"^[{SHORTUUID_ALPHABET}]{{{ID_LENGTH}}}$"
_SHORTUUID_PATTERN = re.compile(SHORTUUID_PATTERN)

# Local part: atom dipisah titik, sehingga titik di awal/akhir atau berurutan
# (``.a@x.com``, ``a.@x.com``, ``a..b@x.com``) ditolak.
# Domain: label alfanumerik (dash hanya di tengah) diakhiri TLD alfabetik.
_EMAIL_PATTERN = re.compile(
    r"^(?P<local>[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*)"
    r"@"
    r"(?P<domain>(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63})$"
)


def normalize_username(value: object) -> str:
    """Validasi username (atribut Moodle) dan buang spasi di tepi.

    Username wajib terisi dan tidak boleh mengandung spasi: kolomnya ``UNIQUE``
    dan dipakai Moodle sebagai identitas login user di sana, sehingga nilai
    ambigu (kosong/spasi) tidak berguna untuk keduanya. Case **tidak** dipaksa
    lowercase di sini — perbedaan besar-kecil huruf adalah kebijakan sistem
    tujuan (Moodle), bukan aturan domain aplikasi ini.
    """
    if not isinstance(value, str):
        raise UserValidationError("username", "harus berupa teks")

    username = value.strip()
    if not username:
        raise UserValidationError("username", "tidak boleh kosong atau hanya spasi")
    if any(char.isspace() for char in username):
        raise UserValidationError("username", "tidak boleh mengandung spasi")
    if any(not char.isprintable() for char in username):
        raise UserValidationError("username", "tidak boleh mengandung karakter kontrol")
    if len(username) > MAX_USERNAME_LENGTH:
        raise UserValidationError(
            "username", f"maksimal {MAX_USERNAME_LENGTH} karakter"
        )
    return username


def normalize_firstname(value: object) -> str:
    """Validasi nama depan (atribut ``firstname`` Moodle) dan buang spasi di tepi."""
    return _normalize_person_name(
        value, field="firstname", maximum=MAX_FIRSTNAME_LENGTH
    )


def normalize_lastname(value: object) -> str:
    """Validasi nama belakang (atribut ``lastname`` Moodle) dan buang spasi di tepi."""
    return _normalize_person_name(
        value, field="lastname", maximum=MAX_LASTNAME_LENGTH
    )


def normalize_email(value: object) -> str:
    """Validasi email dan normalisasi ke huruf kecil.

    Email adalah identity attribute authentication (``users.email`` UNIQUE).
    PostgreSQL membandingkan string secara case-sensitive, sehingga normalisasi
    lowercase di domain mencegah ``Dosen@itk.ac.id`` dan ``dosen@itk.ac.id``
    menjadi dua user berbeda.
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


def normalize_password(value: object) -> str | None:
    """Validasi credential tersimpan pada kolom ``users.password``.

    Nilai ini adalah **hash** bcrypt (lihat :mod:`src.services.auth.passwords`),
    bukan password mentah: spasi ditolak justru agar password mentah tidak
    pernah tersimpan. ``None`` berarti user tidak memakai local authentication,
    jadi tidak ada pemaksaan credential di domain.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise UserValidationError("password", "harus berupa teks atau None")

    digest = value.strip()
    if not digest:
        raise UserValidationError(
            "password", "tidak boleh kosong; gunakan None bila tidak memakai local authentication"
        )
    if any(char.isspace() for char in digest):
        raise UserValidationError(
            "password", "harus berupa hash, bukan password mentah"
        )
    if len(digest) > MAX_PASSWORD_HASH_LENGTH:
        raise UserValidationError(
            "password", f"maksimal {MAX_PASSWORD_HASH_LENGTH} karakter"
        )
    return digest


def normalize_identifier(value: object) -> str | None:
    """Validasi identifier User (ShortUUID, 22 karakter) yang belum tentu tersedia.

    ``None`` pada user yang belum dipersist, karena identifier dibentuk oleh
    database foundation (BE-02). Identifier yang tidak berbentuk ShortUUID
    ditolak di sini supaya nilai cacat tidak pernah sampai ke query database.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise UserValidationError("id", "harus berupa teks atau None")

    identifier = value.strip()
    if not _SHORTUUID_PATTERN.match(identifier):
        raise UserValidationError(
            "id", f"bukan ShortUUID {ID_LENGTH} karakter yang valid: {value!r}"
        )
    return identifier


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


def _normalize_person_name(value: object, *, field: str, maximum: int) -> str:
    """Aturan bersama ``firstname``/``lastname``: teks terisi tanpa karakter kontrol."""
    if not isinstance(value, str):
        raise UserValidationError(field, "harus berupa teks")

    name = value.strip()
    if not name:
        raise UserValidationError(field, "tidak boleh kosong atau hanya spasi")
    if any(not char.isprintable() for char in name):
        raise UserValidationError(field, "tidak boleh mengandung karakter kontrol")
    if len(name) > maximum:
        raise UserValidationError(field, f"maksimal {maximum} karakter")
    return name


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
