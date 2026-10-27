"""Seed setup default dosen uji (BE-10.1).

Akun dosen uji (BE-06.3) harus langsung punya setup default: learning material
aktif, jenis aktivitas lain nonaktif, profile kosong. Dengan begitu halaman
Instructor Setup dapat dibuka tanpa langkah tambahan dan agent sudah punya
konfigurasi aktivitas yang pasti.

Operasi ini **idempotent** dan tidak pernah menimpa setup yang sudah diisi dosen
— seed hanya mengisi baris yang belum ada.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.instructor.service import InstructorSetupService
from src.services.seed.test_accounts import INSTRUCTOR_ACCOUNT, SeedError
from src.services.user.service import UserService

__all__ = ["seed_instructor_setup"]


async def seed_instructor_setup(session: AsyncSession) -> bool:
    """Beri setup default pada akun dosen uji; ``True`` bila baris dibuat.

    Dijalankan setelah :func:`src.services.seed.test_accounts.seed_test_accounts`,
    karena setup merujuk pada user hasil seed.
    """
    user = await UserService.from_session(session).find_user_by_email(INSTRUCTOR_ACCOUNT.email)
    if user is None:
        raise SeedError(
            f"Akun {INSTRUCTOR_ACCOUNT.email} belum ada; jalankan seed akun uji lebih dulu."
        )

    return await InstructorSetupService.from_session(session).ensure_default_setup(user.id)
