"""Seed akun uji instructor dan student (BE-06.3).

Script ini membuat dua akun yang dipakai tim frontend/backend untuk menguji
authentication dan authorization melalui API. Operasi seed bersifat idempotent:
menjalankannya dua kali tidak membuat akun duplikat.

Password **tidak** disimpan di repository dan tidak memiliki nilai default.
Berikan lewat environment (disarankan) atau argumen CLI, atau minta script
membuatkan password acak sekali pakai.

Pemakaian (dari folder ``backend/``)::

    # 1. Password dari environment (tidak muncul di process list/shell history)
    SEED_INSTRUCTOR_PASSWORD='...' \\
    SEED_STUDENT_PASSWORD='...' \\
    uv run python -m scripts.seed_test_accounts

    # 2. Script membuatkan password acak dan menampilkannya sekali
    uv run python -m scripts.seed_test_accounts --generate-passwords

    # 3. Argumen CLI (hati-hati: password dapat terlihat di process list)
    uv run python -m scripts.seed_test_accounts \\
        --instructor-password '...' --student-password '...'

Prasyarat: database dapat dijangkau dan migrasi sudah diterapkan
(``uv run alembic upgrade head``). Jalankan dari Docker dengan:

    docker compose exec backend uv run python -m scripts.seed_test_accounts --generate-passwords

Password akun uji dibagikan melalui kanal internal tim; jangan commit nilainya.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import secrets
import sys
from collections.abc import Mapping, Sequence

from sqlalchemy.exc import SQLAlchemyError

from src.config.database import dispose_engine, get_session_factory
from src.services.seed import (
    INSTRUCTOR_ACCOUNT,
    STUDENT_ACCOUNT,
    SeedConfigurationError,
    SeedError,
    SeedResult,
    seed_instructor_setup,
    seed_test_accounts,
    validate_seed_password,
)

ENV_INSTRUCTOR_PASSWORD = "SEED_INSTRUCTOR_PASSWORD"
ENV_STUDENT_PASSWORD = "SEED_STUDENT_PASSWORD"

# Panjang password acak; jauh di atas minimum 8 karakter.
GENERATED_PASSWORD_BYTES = 12

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_CONFIGURATION = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.seed_test_accounts",
        description=(
            "Buat/perbarui akun uji instructor dan student secara idempotent. "
            "Password tidak disimpan di repository."
        ),
        epilog=(
            "Password dapat diberikan lewat environment "
            f"{ENV_INSTRUCTOR_PASSWORD} dan {ENV_STUDENT_PASSWORD}, argumen CLI, "
            "atau --generate-passwords."
        ),
    )
    parser.add_argument(
        "--instructor-password",
        default=None,
        help=(
            "Password akun instructor. Bila kosong, dibaca dari "
            f"${ENV_INSTRUCTOR_PASSWORD}."
        ),
    )
    parser.add_argument(
        "--student-password",
        default=None,
        help=(
            "Password akun student. Bila kosong, dibaca dari "
            f"${ENV_STUDENT_PASSWORD}."
        ),
    )
    parser.add_argument(
        "--generate-passwords",
        action="store_true",
        help=(
            "Buat password acak untuk akun yang password-nya belum diberikan, "
            "lalu tampilkan sekali di akhir."
        ),
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def resolve_passwords(
    args: argparse.Namespace,
    environ: Mapping[str, str] | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Tentukan password tiap akun dari CLI, environment, atau generator.

    Mengembalikan ``(passwords_by_username, generated_by_username)``. Password
    yang dihasilkan hanya dikembalikan agar pemanggil dapat menampilkannya
    sekali; password dari environment/argumen tidak pernah ditampilkan.
    """
    environment = os.environ if environ is None else environ
    passwords = {
        INSTRUCTOR_ACCOUNT.username: (
            args.instructor_password or environment.get(ENV_INSTRUCTOR_PASSWORD, "")
        ),
        STUDENT_ACCOUNT.username: (
            args.student_password or environment.get(ENV_STUDENT_PASSWORD, "")
        ),
    }

    generated: dict[str, str] = {}
    if getattr(args, "generate_passwords", False):
        for username, password in list(passwords.items()):
            if not password:
                password = secrets.token_urlsafe(GENERATED_PASSWORD_BYTES)
                passwords[username] = password
                generated[username] = password

    # Validasi seluruh akun sebelum database disentuh.
    for username, password in passwords.items():
        validate_seed_password(password, label=username)

    return passwords, generated


async def _run_seed(passwords: Mapping[str, str]) -> tuple[list[SeedResult], bool]:
    """Seed akun uji, lalu setup default dosen (BE-10.1) pada session yang sama."""
    session_factory = get_session_factory()
    try:
        async with session_factory() as session:
            results = await seed_test_accounts(session, passwords=passwords)
            setup_created = await seed_instructor_setup(session)
            return results, setup_created
    finally:
        await dispose_engine()


def _print_results(
    results: list[SeedResult],
    generated: Mapping[str, str],
    setup_created: bool = False,
) -> None:
    print("Seed akun uji selesai:")
    for result in results:
        account = result.account
        print(
            f"  {result.action.value:<9} {account.role.value:<10} "
            f"{account.username:<15} {account.email}"
        )

    print(
        "  setup dosen: "
        + ("dibuat (learning material aktif)" if setup_created else "sudah ada, tidak diubah")
    )

    if generated:
        print("\nPassword akun yang dibuat (tampil sekali; simpan di kanal internal):")
        for username, password in generated.items():
            print(f"  {username}: {password}")
        print(
            "Password tidak disimpan di repository. Jalankan ulang seed dengan "
            "password yang sama untuk mempertahankannya."
        )
    else:
        print("\nPassword tidak ditampilkan (berasal dari environment/argumen).")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        passwords, generated = resolve_passwords(args)
    except SeedConfigurationError as exc:
        print(f"Seed gagal: {exc}", file=sys.stderr)
        return EXIT_CONFIGURATION

    try:
        results, setup_created = asyncio.run(_run_seed(passwords))
    except SeedConfigurationError as exc:
        print(f"Seed gagal: {exc}", file=sys.stderr)
        return EXIT_CONFIGURATION
    except SeedError as exc:
        print(f"Seed gagal: {exc}", file=sys.stderr)
        return EXIT_FAILURE
    except SQLAlchemyError as exc:
        print(
            "Seed gagal: database tidak dapat diakses "
            f"({type(exc).__name__}). Pastikan PostgreSQL berjalan dan migrasi "
            "sudah diterapkan (uv run alembic upgrade head).",
            file=sys.stderr,
        )
        return EXIT_FAILURE

    _print_results(results, generated, setup_created)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
