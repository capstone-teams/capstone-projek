"""Test seed akun uji instructor/student (BE-06.3).

Yang diuji:

- seed membuat satu akun instructor dan satu akun student;
- seed dapat dijalankan dua kali tanpa membuat baris duplikat;
- perubahan role/nama/status/password diperbarui secara idempotent;
- password invalid ditolak sebelum database disentuh;
- konflik identitas tidak menimpa user lain;
- akun hasil seed benar-benar dapat login melalui API dan ``/auth/me``;
- resolusi password CLI/environment tidak pernah menampilkan credential dari
  environment.

Pengujian memakai session database yang sama dengan test lain (lihat
``tests/conftest.py``) sehingga tidak perlu server terpisah. Password hanya
berupa nilai test yang dibuat di file ini, bukan credential tim.
"""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from src.main import create_app
from src.services.auth import hash_password, verify_password
from src.services.dependencies import get_db_session
from src.services.seed import (
    DEFAULT_SEED_ACCOUNTS,
    INSTRUCTOR_ACCOUNT,
    STUDENT_ACCOUNT,
    SeedAction,
    SeedConflictError,
    SeedConfigurationError,
    seed_test_accounts,
)
from src.services.user import UserRole, UserService, UserStatus
from scripts.seed_test_accounts import (
    ENV_INSTRUCTOR_PASSWORD,
    ENV_STUDENT_PASSWORD,
    parse_args,
    resolve_passwords,
)

INSTRUCTOR_PASSWORD = "PasswordDosenUji123"
STUDENT_PASSWORD = "PasswordMahasiswaUji123"
PASSWORDS = {
    INSTRUCTOR_ACCOUNT.username: INSTRUCTOR_PASSWORD,
    STUDENT_ACCOUNT.username: STUDENT_PASSWORD,
}
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"


@pytest_asyncio.fixture
async def user_service(db_session) -> UserService:
    return UserService.from_session(db_session)


@pytest_asyncio.fixture
async def client(db_session) -> httpx.AsyncClient:
    application = create_app()

    async def override_get_db_session():
        yield db_session

    application.dependency_overrides[get_db_session] = override_get_db_session
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client
    application.dependency_overrides.clear()


async def seed(db_session, passwords=None):
    return await seed_test_accounts(db_session, passwords=passwords or PASSWORDS)


async def users_by_email(user_service: UserService) -> dict[str, object]:
    return {user.email: user for user in await user_service.list_users()}


# ---------------------------------------------------------------------------
# Definisi akun
# ---------------------------------------------------------------------------


def test_default_accounts_cover_one_instructor_and_one_student():
    roles = [account.role for account in DEFAULT_SEED_ACCOUNTS]

    assert roles == [UserRole.INSTRUCTOR, UserRole.STUDENT]
    assert len({account.email for account in DEFAULT_SEED_ACCOUNTS}) == 2
    assert len({account.username for account in DEFAULT_SEED_ACCOUNTS}) == 2


# ---------------------------------------------------------------------------
# Membuat dan mengulang seed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_creates_instructor_and_student(db_session, user_service):
    results = await seed(db_session)

    assert [result.action for result in results] == [
        SeedAction.CREATED,
        SeedAction.CREATED,
    ]
    users = await users_by_email(user_service)
    instructor = users[INSTRUCTOR_ACCOUNT.email]
    student = users[STUDENT_ACCOUNT.email]

    assert instructor.role is UserRole.INSTRUCTOR
    assert student.role is UserRole.STUDENT
    assert instructor.status is UserStatus.ACTIVE
    assert student.status is UserStatus.ACTIVE
    assert verify_password(INSTRUCTOR_PASSWORD, instructor.password)
    assert verify_password(STUDENT_PASSWORD, student.password)


@pytest.mark.asyncio
async def test_seed_can_run_twice_without_duplicates(db_session, user_service):
    first = await seed(db_session)
    second = await seed(db_session)

    assert [result.action for result in second] == [
        SeedAction.UNCHANGED,
        SeedAction.UNCHANGED,
    ]
    assert [result.user_id for result in first] == [result.user_id for result in second]
    assert len(await user_service.list_users()) == 2


@pytest.mark.asyncio
async def test_seed_restores_role_name_and_active_status(db_session, user_service):
    await seed(db_session)
    instructor = (await users_by_email(user_service))[INSTRUCTOR_ACCOUNT.email]
    await user_service.update_user(instructor.id, firstname="Berubah", role=UserRole.STUDENT)
    await user_service.deactivate_user(instructor.id)

    results = await seed(db_session)

    assert results[0].action is SeedAction.UPDATED
    restored = (await users_by_email(user_service))[INSTRUCTOR_ACCOUNT.email]
    assert restored.firstname == INSTRUCTOR_ACCOUNT.firstname
    assert restored.role is UserRole.INSTRUCTOR
    assert restored.status is UserStatus.ACTIVE


@pytest.mark.asyncio
async def test_seed_only_rewrites_password_when_it_changed(db_session, user_service):
    await seed(db_session)
    original = (await users_by_email(user_service))[INSTRUCTOR_ACCOUNT.email]

    results = await seed(
        db_session,
        passwords={
            INSTRUCTOR_ACCOUNT.username: "PasswordBaruDosen123",
            STUDENT_ACCOUNT.username: STUDENT_PASSWORD,
        },
    )

    assert results[0].action is SeedAction.UPDATED
    assert results[1].action is SeedAction.UNCHANGED
    updated = (await users_by_email(user_service))[INSTRUCTOR_ACCOUNT.email]
    assert updated.password != original.password
    assert verify_password("PasswordBaruDosen123", updated.password)
    assert not verify_password(INSTRUCTOR_PASSWORD, updated.password)


# ---------------------------------------------------------------------------
# Validasi dan konflik
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("password", ["", "pendek", "x" * 73])
async def test_invalid_password_is_rejected_before_any_write(db_session, user_service, password):
    with pytest.raises(SeedConfigurationError):
        await seed(
            db_session,
            passwords={
                INSTRUCTOR_ACCOUNT.username: password,
                STUDENT_ACCOUNT.username: STUDENT_PASSWORD,
            },
        )

    assert await user_service.list_users() == []


@pytest.mark.asyncio
async def test_seed_does_not_take_a_username_owned_by_another_user(db_session, user_service):
    await user_service.create_user(
        username=INSTRUCTOR_ACCOUNT.username,
        firstname="User",
        lastname="Lain",
        email="user.lain@itk.ac.id",
        role=UserRole.STUDENT,
        password=hash_password("PasswordUserLain123"),
    )

    with pytest.raises(SeedConflictError):
        await seed(db_session)

    users = await user_service.list_users()
    assert [user.email for user in users] == ["user.lain@itk.ac.id"]


@pytest.mark.asyncio
async def test_seed_result_never_contains_the_password(db_session):
    results = await seed(db_session)

    rendered = repr(results)
    assert INSTRUCTOR_PASSWORD not in rendered
    assert STUDENT_PASSWORD not in rendered
    assert "$2b$" not in rendered


# ---------------------------------------------------------------------------
# Akun hasil seed dipakai lewat API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "account,password",
    [
        (INSTRUCTOR_ACCOUNT, INSTRUCTOR_PASSWORD),
        (STUDENT_ACCOUNT, STUDENT_PASSWORD),
    ],
    ids=["instructor", "student"],
)
@pytest.mark.parametrize("identifier_field", ["username", "email"])
async def test_seeded_accounts_can_login_through_the_api(
    client, db_session, account, password, identifier_field
):
    await seed(db_session)
    identifier = getattr(account, identifier_field)

    login = await client.post(
        LOGIN_URL,
        json={"username": identifier, "password": password},
    )

    assert login.status_code == 200
    body = login.json()
    assert body["user"]["role"] == account.role.value
    assert body["token_type"] == "bearer"

    me = await client.get(
        ME_URL,
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == account.email
    assert me.json()["role"] == account.role.value


# ---------------------------------------------------------------------------
# Script CLI
# ---------------------------------------------------------------------------


def test_cli_reads_passwords_from_environment():
    args = parse_args([])

    passwords, generated = resolve_passwords(
        args,
        {
            ENV_INSTRUCTOR_PASSWORD: INSTRUCTOR_PASSWORD,
            ENV_STUDENT_PASSWORD: STUDENT_PASSWORD,
        },
    )

    assert passwords == PASSWORDS
    assert generated == {}


def test_cli_flags_override_environment():
    args = parse_args(
        [
            "--instructor-password",
            "PasswordFlagDosen123",
            "--student-password",
            "PasswordFlagMahasiswa123",
        ]
    )

    passwords, generated = resolve_passwords(
        args,
        {
            ENV_INSTRUCTOR_PASSWORD: "PasswordEnvDosen123",
            ENV_STUDENT_PASSWORD: "PasswordEnvMahasiswa123",
        },
    )

    assert passwords[INSTRUCTOR_ACCOUNT.username] == "PasswordFlagDosen123"
    assert passwords[STUDENT_ACCOUNT.username] == "PasswordFlagMahasiswa123"
    assert generated == {}


def test_cli_generates_only_the_missing_password():
    args = parse_args(
        ["--generate-passwords", "--instructor-password", "PasswordDosenTetap123"]
    )

    passwords, generated = resolve_passwords(args, {})

    assert passwords[INSTRUCTOR_ACCOUNT.username] == "PasswordDosenTetap123"
    assert INSTRUCTOR_ACCOUNT.username not in generated
    assert passwords[STUDENT_ACCOUNT.username]
    assert generated == {STUDENT_ACCOUNT.username: passwords[STUDENT_ACCOUNT.username]}


def test_cli_requires_a_password_without_generate_flag():
    with pytest.raises(SeedConfigurationError):
        resolve_passwords(parse_args([]), {})


def test_cli_rejects_short_password():
    with pytest.raises(SeedConfigurationError):
        resolve_passwords(
            parse_args(
                [
                    "--instructor-password",
                    "pendek",
                    "--student-password",
                    STUDENT_PASSWORD,
                ]
            ),
            {},
        )
