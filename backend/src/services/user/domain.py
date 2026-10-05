"""Representasi domain User.

``User`` di sini adalah domain model, bukan entity persistence: ia hanya memuat
aturan identity dan lifecycle, tidak tahu tabel, session, maupun SQLAlchemy.
Entity tabelnya tetap ``src.models.user.User`` (BE-02) yang diakses melalui
User Service/User Repository (BE-03.2). Pemisahan ini menjaga agar perubahan
persistence tidak menyebar ke application layer, dan sebaliknya.

Nama field identity mengikuti atribut user Moodle (``username``, ``firstname``,
``lastname``, ``email``, ``password``) supaya sinkronisasi user ke Moodle tidak
perlu penerjemahan nama field. Yang **tidak** ada di sini tetap sama seperti
sebelumnya:

- detail integrasi Moodle (base URL, token, ``moodle_user_id``, dsb. — BE-04);
- identity/permission agent atau LLM;
- apa pun dari HTTP layer (request/response/FastAPI).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.services.user.enums import UserRole, UserStatus
from src.services.user.validation import (
    normalize_email,
    normalize_firstname,
    normalize_identifier,
    normalize_lastname,
    normalize_password,
    normalize_role,
    normalize_status,
    normalize_timestamp,
    normalize_username,
)

__all__ = ["User"]


@dataclass(kw_only=True, slots=True)
class User:
    """User aplikasi beserta role, status, dan metadata lifecycle-nya.

    Setiap ``User`` yang berhasil dibentuk sudah tervalidasi dan ternormalisasi
    (username/nama tanpa spasi di tepi, email lowercase, role/status berupa enum
    kanonik), sehingga invariant domain tetap terjaga di seluruh application
    layer.

    ``password`` adalah **hash** bcrypt, bukan password mentah: password hanya
    ada pada saat provisioning ke Moodle dan tidak pernah disimpan.
    """

    username: str
    firstname: str
    lastname: str
    email: str
    role: UserRole
    status: UserStatus = UserStatus.ACTIVE
    id: str | None = None
    password: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self.username = normalize_username(self.username)
        self.firstname = normalize_firstname(self.firstname)
        self.lastname = normalize_lastname(self.lastname)
        self.email = normalize_email(self.email)
        self.role = normalize_role(self.role)
        self.status = normalize_status(self.status)
        self.password = normalize_password(self.password)
        self.id = normalize_identifier(self.id)
        self.created_at = normalize_timestamp(self.created_at, "created_at")
        self.updated_at = normalize_timestamp(self.updated_at, "updated_at")

    @classmethod
    def create(
        cls,
        *,
        username: str,
        firstname: str,
        lastname: str,
        email: str,
        role: UserRole | str,
        password: str | None = None,
    ) -> "User":
        """Membentuk user baru yang belum dipersist.

        User baru selalu berstatus ``ACTIVE``; identifier dan timestamp
        dibiarkan ``None`` karena dibentuk oleh database. ``password`` berisi
        hash (lihat :mod:`src.services.auth.passwords`), bukan password mentah.
        """
        return cls(
            username=username,
            firstname=firstname,
            lastname=lastname,
            email=email,
            role=role,
            status=UserStatus.ACTIVE,
            password=password,
        )

    @property
    def is_active(self) -> bool:
        """Apakah user boleh dipakai untuk mengakses aplikasi."""
        return self.status is UserStatus.ACTIVE

    @property
    def uses_local_authentication(self) -> bool:
        """Apakah user punya credential lokal.

        Relevan untuk authentication (BE-03.3): user tanpa ``password``
        tidak dapat login dengan mekanisme credential lokal.
        """
        return self.password is not None

    def can_authenticate(self) -> bool:
        """Aturan lifecycle: hanya user ACTIVE yang boleh terautentikasi.

        User INACTIVE dipertahankan sebagai catatan (hard delete tidak dipakai,
        lihat Deletion Strategy pada data model), tetapi tidak boleh dipakai
        untuk mengakses aplikasi.
        """
        return self.is_active

    def activate(self) -> None:
        """Mengaktifkan kembali user (idempoten)."""
        self.status = UserStatus.ACTIVE

    def deactivate(self) -> None:
        """Menonaktifkan user (idempoten).

        Deaktivasi adalah cara standar menonaktifkan user, bukan penghapusan
        permanen.
        """
        self.status = UserStatus.INACTIVE

    def change_role(self, role: UserRole | str) -> None:
        """Mengubah role user dengan tetap melewati validasi domain."""
        self.role = normalize_role(role)

    def __str__(self) -> str:
        # Jangan pernah menampilkan credential pada representasi user.
        return f"User(id={self.id}, username={self.username}, email={self.email}, role={self.role.value}, status={self.status.value})"

    def __repr__(self) -> str:
        # Hash tidak ikut direpresentasikan supaya credential tidak bocor
        # melalui log, traceback, maupun pesan error.
        password = "set" if self.password else "unset"
        return (
            f"User(id={self.id!r}, username={self.username!r}, "
            f"firstname={self.firstname!r}, lastname={self.lastname!r}, "
            f"email={self.email!r}, role={self.role.value!r}, "
            f"status={self.status.value!r}, password={password}, "
            f"created_at={self.created_at!r}, updated_at={self.updated_at!r})"
        )
