"""Representasi domain User.

``User`` di sini adalah domain model, bukan entity persistence: ia hanya memuat
aturan identity dan lifecycle, tidak tahu tabel, session, maupun SQLAlchemy.
Entity tabelnya tetap ``src.models.user.User`` (BE-02) yang diakses melalui
User Service/User Repository (BE-03.2). Pemisahan ini menjaga agar perubahan
persistence tidak menyebar ke application layer, dan sebaliknya.

Model ini sengaja tidak memuat:
- field spesifik Moodle (Moodle user adalah entity terpisah pada BE-04);
- identity/permission agent atau LLM;
- apa pun dari HTTP layer (request/response/FastAPI).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from src.services.user.enums import UserRole, UserStatus
from src.services.user.validation import (
    normalize_email,
    normalize_identifier,
    normalize_name,
    normalize_password_hash,
    normalize_role,
    normalize_status,
    normalize_timestamp,
)

__all__ = ["User"]


@dataclass(kw_only=True, slots=True)
class User:
    """User aplikasi beserta role, status, dan metadata lifecycle-nya.

    Setiap ``User`` yang berhasil dibentuk sudah tervalidasi dan ternormalisasi
    (name tanpa spasi di tepi, email lowercase, role/status berupa enum kanonik),
    sehingga invariant domain tetap terjaga di seluruh application layer.
    """

    name: str
    email: str
    role: UserRole
    status: UserStatus = UserStatus.ACTIVE
    id: uuid.UUID | None = None
    password_hash: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self.name = normalize_name(self.name)
        self.email = normalize_email(self.email)
        self.role = normalize_role(self.role)
        self.status = normalize_status(self.status)
        self.password_hash = normalize_password_hash(self.password_hash)
        self.id = normalize_identifier(self.id)
        self.created_at = normalize_timestamp(self.created_at, "created_at")
        self.updated_at = normalize_timestamp(self.updated_at, "updated_at")

    @classmethod
    def create(
        cls,
        *,
        name: str,
        email: str,
        role: UserRole | str,
        password_hash: str | None = None,
    ) -> "User":
        """Membentuk user baru yang belum dipersist.

        User baru selalu berstatus ``ACTIVE``; identifier dan timestamp
        dibiarkan ``None`` karena dibentuk oleh database.
        """
        return cls(
            name=name,
            email=email,
            role=role,
            status=UserStatus.ACTIVE,
            password_hash=password_hash,
        )

    @property
    def is_active(self) -> bool:
        """Apakah user boleh dipakai untuk mengakses aplikasi."""
        return self.status is UserStatus.ACTIVE

    @property
    def uses_local_authentication(self) -> bool:
        """Apakah user punya credential lokal.

        Relevan untuk authentication (BE-03.3): user tanpa ``password_hash``
        tidak dapat login dengan mekanisme credential lokal.
        """
        return self.password_hash is not None

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
        # Jangan pernah menampilkan password_hash pada representasi user.
        return f"User(id={self.id}, email={self.email}, role={self.role.value}, status={self.status.value})"

    def __repr__(self) -> str:
        # Password hash tidak ikut direpresentasikan supaya credential tidak
        # bocor melalui log, traceback, maupun pesan error.
        password_hash = "set" if self.password_hash else "unset"
        return (
            f"User(id={self.id!r}, name={self.name!r}, email={self.email!r}, "
            f"role={self.role.value!r}, status={self.status.value!r}, "
            f"password_hash={password_hash}, created_at={self.created_at!r}, "
            f"updated_at={self.updated_at!r})"
        )
