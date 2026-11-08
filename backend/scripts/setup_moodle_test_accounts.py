"""Siapkan akun, course, dan enrolment uji di Moodle tim (BE-04.5).

Membuat (bila belum ada) satu dosen dan dua mahasiswa uji, satu course uji,
lalu mendaftarkan dosen sebagai teacher dan kedua mahasiswa sebagai student.
Seluruh operasi berjalan lewat Moodle Integration Layer dan aman dijalankan
berulang kali: akun dan course yang sudah ada dipakai ulang, password akun yang
sudah ada tidak diubah, dan enrolment ulang tidak membuat data ganda.

Akun ini milik **Moodle**, terpisah dari akun aplikasi hasil
``scripts.seed_test_accounts`` (BE-06.3).

Password **tidak** disimpan di repository dan tidak memiliki nilai default.
Berikan lewat environment (disarankan) atau minta script membuatkan password
acak yang ditampilkan sekali::

    # 1. Password dari environment
    MOODLE_TEST_TEACHER_PASSWORD='...' MOODLE_TEST_STUDENT_PASSWORD='...' \\
    uv run python -m scripts.setup_moodle_test_accounts

    # 2. Password acak, ditampilkan sekali
    uv run python -m scripts.setup_moodle_test_accounts --generate-passwords

Prasyarat: ``MOODLE_BASE_URL`` dan ``MOODLE_WEB_SERVICE_TOKEN`` di ``.env`` benar,
dan service web Moodle memuat ``core_user_create_users``,
``core_user_get_users_by_field``, ``enrol_manual_enrol_users``,
``core_enrol_get_enrolled_users``, ``core_course_get_courses_by_field``, dan
``core_course_create_courses``. Bagikan password lewat kanal internal tim;
jangan commit nilainya.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import secrets
import string
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from src.config.settings import settings
from src.services.moodle_adapter_exceptions import MoodleEntityNotFoundError
from src.services.moodle_client import MoodleClient
from src.services.moodle_exceptions import MoodleError
from src.services.moodle_integration_service import MoodleIntegrationService

ENV_TEACHER_PASSWORD = "MOODLE_TEST_TEACHER_PASSWORD"
ENV_STUDENT_PASSWORD = "MOODLE_TEST_STUDENT_PASSWORD"

DEFAULT_COURSE_SHORTNAME = "capstone-uji"
DEFAULT_COURSE_FULLNAME = "Course Uji Capstone"
DEFAULT_CATEGORY_ID = 1


@dataclass(frozen=True)
class MoodleTestAccount:
    username: str
    firstname: str
    lastname: str
    role: str  # "teacher" atau "student"

    @property
    def email(self) -> str:
        return f"{self.username}@example.com"


TEST_ACCOUNTS = (
    MoodleTestAccount("dosen.uji", "Dosen", "Uji", "teacher"),
    MoodleTestAccount("mhs.uji", "Mahasiswa", "Uji", "student"),
    MoodleTestAccount("mhs.uji2", "Mahasiswa", "Uji Dua", "student"),
)


@dataclass(frozen=True)
class AccountResult:
    account: MoodleTestAccount
    moodle_user_id: int
    created: bool
    password: str | None  # hanya diisi bila akun baru dibuat dengan password acak


@dataclass(frozen=True)
class SetupResult:
    moodle_course_id: int
    course_shortname: str
    course_created: bool
    accounts: tuple[AccountResult, ...]


class SetupConfigurationError(ValueError):
    """Konfigurasi script tidak lengkap (misalnya password tidak diberikan)."""


def generate_password() -> str:
    """Password acak yang memenuhi password policy bawaan Moodle."""
    alphabet = string.ascii_letters + string.digits
    core = "".join(secrets.choice(alphabet) for _ in range(12))
    return core + secrets.choice(string.ascii_uppercase) + secrets.choice(string.digits) + "#"


def resolve_password(account: MoodleTestAccount, *, generate: bool, env: Mapping[str, str]) -> tuple[str, bool]:
    """Password untuk akun baru dan apakah password itu dibuat acak."""
    if generate:
        return generate_password(), True
    variable = ENV_TEACHER_PASSWORD if account.role == "teacher" else ENV_STUDENT_PASSWORD
    password = env.get(variable, "").strip()
    if not password:
        raise SetupConfigurationError(
            f"Password untuk akun baru '{account.username}' belum ada. Isi {variable} "
            "atau jalankan dengan --generate-passwords."
        )
    return password, False


async def setup_test_environment(
    service: MoodleIntegrationService,
    *,
    course_shortname: str = DEFAULT_COURSE_SHORTNAME,
    course_fullname: str = DEFAULT_COURSE_FULLNAME,
    category_id: int = DEFAULT_CATEGORY_ID,
    accounts: Sequence[MoodleTestAccount] = TEST_ACCOUNTS,
    generate_passwords: bool = False,
    env: Mapping[str, str] | None = None,
) -> SetupResult:
    """Pastikan course uji, akun uji, dan enrolment-nya ada di Moodle."""
    env = os.environ if env is None else env

    try:
        course = await service.get_course_by_shortname(course_shortname)
        course_created = False
    except MoodleEntityNotFoundError:
        course = await service.create_course(course_fullname, course_shortname, category_id)
        course_created = True

    results = []
    for account in accounts:
        user = await service.get_user_by_username(account.username)
        if user is not None:
            results.append(AccountResult(account, user.moodle_user_id, created=False, password=None))
            continue
        password, generated = resolve_password(account, generate=generate_passwords, env=env)
        user = await service.create_user(
            username=account.username,
            password=password,
            firstname=account.firstname,
            lastname=account.lastname,
            email=account.email,
        )
        results.append(
            AccountResult(account, user.moodle_user_id, created=True, password=password if generated else None)
        )

    await service.enrol_users(
        course.moodle_course_id, [(result.moodle_user_id, result.account.role) for result in results]
    )
    return SetupResult(
        moodle_course_id=course.moodle_course_id,
        course_shortname=course.shortname,
        course_created=course_created,
        accounts=tuple(results),
    )


def format_report(result: SetupResult) -> str:
    course_status = "dibuat" if result.course_created else "sudah ada"
    lines = [
        "Setup Moodle uji selesai:",
        f"  course   {result.course_shortname} (id {result.moodle_course_id}): {course_status}",
    ]
    for item in result.accounts:
        status = "dibuat" if item.created else "sudah ada, password tidak diubah"
        lines.append(f"  {item.account.role:<8} {item.account.username:<10} (id {item.moodle_user_id}): {status}")
    generated = [item for item in result.accounts if item.password]
    if generated:
        lines += ["", "Password acak (ditampilkan sekali, bagikan lewat kanal internal tim):"]
        lines += [f"  {item.account.username:<10} {item.password}" for item in generated]
    lines.append("Semua akun terdaftar di course: dosen sebagai teacher, mahasiswa sebagai student.")
    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.setup_moodle_test_accounts",
        description="Siapkan akun dosen/mahasiswa uji, course uji, dan enrolment di Moodle secara idempotent.",
    )
    parser.add_argument("--course-shortname", default=DEFAULT_COURSE_SHORTNAME)
    parser.add_argument("--course-fullname", default=DEFAULT_COURSE_FULLNAME)
    parser.add_argument("--category-id", type=int, default=DEFAULT_CATEGORY_ID)
    parser.add_argument(
        "--generate-passwords",
        action="store_true",
        help="Buat password acak untuk akun baru dan tampilkan sekali.",
    )
    return parser.parse_args(argv)


async def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    async with MoodleClient.from_settings(settings) as client:
        try:
            result = await setup_test_environment(
                MoodleIntegrationService(client),
                course_shortname=args.course_shortname,
                course_fullname=args.course_fullname,
                category_id=args.category_id,
                generate_passwords=args.generate_passwords,
            )
        except SetupConfigurationError as exc:
            print(f"Konfigurasi belum lengkap: {exc}", file=sys.stderr)
            return 2
        except MoodleError as exc:
            print(f"Moodle menolak operasi ({exc.error_type}, {exc.code}): {exc.message}", file=sys.stderr)
            return 1
    print(format_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))