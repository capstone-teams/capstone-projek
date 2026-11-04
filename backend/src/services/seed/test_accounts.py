"""Seed akun uji instructor dan student (BE-06.3).

Modul ini menyediakan operasi **idempotent** untuk menyiapkan dua akun yang
dipakai tim frontend dan backend saat menguji authentication/authorization:

| Role | Username | Email |
| :--- | :--- | :--- |
| INSTRUCTOR | `dosen.demo` | `dosen.demo@itk.ac.id` |
| STUDENT | `11231023` | `11231023@student.itk.ac.id` |

Identitas student mengikuti konvensi ITK: username adalah NIM dan email adalah
``<NIM>@student.itk.ac.id``. Instructor memakai alamat berbasis nama, bukan NIP
(``<NIP>@dosen.itk.ac.id``).

Password **tidak** ditentukan di repository. Pemanggil wajib memberikannya dari
environment/argumen (lihat ``scripts/seed_test_accounts.py``), sehingga tidak
ada credential yang ter-commit. Password disimpan sebagai hash bcrypt melalui
mekanisme yang sama dengan user biasa.

Idempotensi:

- akun dicari berdasarkan email (identifier yang unik dan stabil);
- field yang sudah sesuai tidak diubah;
- password hanya di-hash ulang bila password yang diberikan tidak cocok dengan
  hash tersimpan;
- role/nama/username yang berbeda diperbarui;
- user non-aktif diaktifkan kembali.

Dengan demikian seed dapat dijalankan berulang tanpa membuat baris duplikat.
Tidak ada logika HTTP di sini; pemanggilan dari route tidak diperlukan.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.auth.passwords import (
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    hash_password,
    verify_password,
)
from src.services.user.domain import User
from src.services.user.enums import UserRole
from src.services.user.errors import DuplicateEmailError, DuplicateUsernameError
from src.services.user.service import UserService

__all__ = [
    "DEFAULT_SEED_ACCOUNTS",
    "INSTRUCTOR_ACCOUNT",
    "STUDENT_ACCOUNT",
    "SeedAccount",
    "SeedAction",
    "SeedConflictError",
    "SeedConfigurationError",
    "SeedError",
    "SeedResult",
    "seed_test_accounts",
    "validate_seed_password",
]


class SeedError(Exception):
    """Kegagalan seed yang aman ditampilkan ke operator (tanpa credential)."""


class SeedConfigurationError(SeedError):
    """Password/konfigurasi seed tidak memenuhi syarat; tidak ada data ditulis."""


class SeedConflictError(SeedError):
    """Username/email akun seed sudah dipakai user lain dengan identitas berbeda."""


class SeedAction(str, Enum):
    """Hasil satu akun pada satu kali eksekusi seed."""

    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


@dataclass(frozen=True, slots=True)
class SeedAccount:
    """Definisi akun uji; password sengaja tidak disimpan di sini."""

    username: str
    firstname: str
    lastname: str
    email: str
    role: UserRole


@dataclass(frozen=True, slots=True)
class SeedResult:
    """Hasil seed satu akun. Tidak pernah memuat password maupun hash."""

    account: SeedAccount
    action: SeedAction
    user_id: str


INSTRUCTOR_ACCOUNT = SeedAccount(
    username="dosen.demo",
    firstname="Dosen",
    lastname="Demo",
    email="dosen.demo@itk.ac.id",
    role=UserRole.INSTRUCTOR,
)

STUDENT_ACCOUNT = SeedAccount(
    username="11231023",
    firstname="Mahasiswa",
    lastname="Demo",
    email="11231023@student.itk.ac.id",
    role=UserRole.STUDENT,
)

DEFAULT_SEED_ACCOUNTS: tuple[SeedAccount, ...] = (
    INSTRUCTOR_ACCOUNT,
    STUDENT_ACCOUNT,
)


async def seed_test_accounts(
    session: AsyncSession,
    *,
    passwords: Mapping[str, str],
    accounts: tuple[SeedAccount, ...] = DEFAULT_SEED_ACCOUNTS,
) -> list[SeedResult]:
    """Buat/perbarui akun uji secara idempotent.

    ``passwords`` dipetakan berdasarkan ``username`` akun. Seluruh password
    divalidasi **sebelum** database disentuh, sehingga konfigurasi yang salah
    tidak meninggalkan akun setengah jadi. Akun dicari berdasarkan email; bila
    email sudah ada, field yang berbeda diperbarui dan password hanya di-hash
    ulang bila perlu.
    """
    _validate_passwords(passwords=passwords, accounts=accounts)

    service = UserService.from_session(session)
    results: list[SeedResult] = []

    for account in accounts:
        password = passwords[account.username]
        existing = await service.find_user_by_email(account.email)

        if existing is None:
            await _ensure_username_is_available(service, account)
            try:
                created = await service.create_user(
                    username=account.username,
                    firstname=account.firstname,
                    lastname=account.lastname,
                    email=account.email,
                    role=account.role,
                    password=hash_password(password),
                )
            except (DuplicateEmailError, DuplicateUsernameError) as exc:
                raise SeedConflictError(
                    f"Akun {account.email} tidak dapat dibuat karena identitasnya "
                    "sudah dipakai user lain"
                ) from exc
            results.append(
                SeedResult(account=account, action=SeedAction.CREATED, user_id=_user_id(created))
            )
            continue

        # User dengan email tersebut sudah ada. Jangan pernah mengubah user lain
        # yang kebetulan memakai username sama.
        if existing.username != account.username:
            await _ensure_username_is_available(service, account, current_id=existing.id)

        changes: dict[str, object] = {}
        if existing.username != account.username:
            changes["username"] = account.username
        if existing.firstname != account.firstname:
            changes["firstname"] = account.firstname
        if existing.lastname != account.lastname:
            changes["lastname"] = account.lastname
        if existing.role != account.role:
            changes["role"] = account.role
        if existing.password is None or not verify_password(password, existing.password):
            changes["password"] = hash_password(password)

        updated = existing
        if changes:
            try:
                updated = await service.update_user(_user_id(existing), **changes)
            except DuplicateUsernameError as exc:
                raise SeedConflictError(
                    f"Username {account.username!r} sudah dipakai user lain"
                ) from exc

        action = SeedAction.UPDATED if changes else SeedAction.UNCHANGED
        if not updated.is_active:
            updated = await service.activate_user(_user_id(updated))
            action = SeedAction.UPDATED

        results.append(
            SeedResult(account=account, action=action, user_id=_user_id(updated))
        )

    return results


def validate_seed_password(password: str, *, label: str) -> None:
    """Validasi password akun uji sebelum hashing/database.

    ``label`` hanya nama akun (mis. ``dosen.demo``), tidak pernah password,
    sehingga pesan error aman ditampilkan dan dicatat.
    """
    if not isinstance(password, str) or not password:
        raise SeedConfigurationError(
            f"Password untuk {label} belum diisi. Set SEED_INSTRUCTOR_PASSWORD / "
            "SEED_STUDENT_PASSWORD atau pakai --generate-passwords."
        )
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SeedConfigurationError(
            f"Password untuk {label} minimal {MIN_PASSWORD_LENGTH} karakter."
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise SeedConfigurationError(
            f"Password untuk {label} maksimal {MAX_PASSWORD_LENGTH} karakter."
        )


def _validate_passwords(
    *,
    passwords: Mapping[str, str],
    accounts: tuple[SeedAccount, ...],
) -> None:
    for account in accounts:
        password = passwords.get(account.username)
        if password is None:
            raise SeedConfigurationError(
                f"Password untuk {account.username} tidak diberikan."
            )
        validate_seed_password(password, label=account.username)


async def _ensure_username_is_available(
    service: UserService,
    account: SeedAccount,
    *,
    current_id: str | None = None,
) -> None:
    """Cegah seed mengambil username milik user lain atau menabrak unique constraint."""
    conflict = await service.find_user_by_username(account.username)
    if conflict is None:
        return
    if current_id is not None and conflict.id == current_id:
        return
    raise SeedConflictError(
        f"Username {account.username!r} sudah dipakai user lain "
        f"({conflict.email}); seed tidak mengubah user tersebut."
    )


def _user_id(user: User) -> str:
    if user.id is None:
        raise SeedError("User hasil seed tidak memiliki identifier.")
    return user.id
