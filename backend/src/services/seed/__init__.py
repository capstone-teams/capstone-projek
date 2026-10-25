"""Seed data akun uji dan setup default dosen (BE-06.3, BE-10.1).

Lihat :mod:`src.services.seed.test_accounts` untuk daftar akun dan
:mod:`src.services.seed.instructor_setup` untuk setup default dosen uji. Keduanya
idempotent dan dipakai script ``scripts/seed_test_accounts.py``.
"""

from src.services.seed.instructor_setup import seed_instructor_setup
from src.services.seed.test_accounts import (
    DEFAULT_SEED_ACCOUNTS,
    INSTRUCTOR_ACCOUNT,
    STUDENT_ACCOUNT,
    SeedAccount,
    SeedAction,
    SeedConflictError,
    SeedConfigurationError,
    SeedError,
    SeedResult,
    seed_test_accounts,
    validate_seed_password,
)

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
    "seed_instructor_setup",
    "seed_test_accounts",
    "validate_seed_password",
]
