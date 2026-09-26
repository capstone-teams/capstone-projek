"""Test mekanisme authentication (BE-03.3) pada SQLite in-memory.

Cakupan: hashing password, penerbitan/validasi token, verifikasi kredensial,
penolakan user non-aktif dan user tanpa credential lokal, serta pembacaan
role/status dari record User (bukan dari klaim token).
"""

import ast
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
import pytest_asyncio

from src.config.settings import settings
from src.services.auth import (
    AuthService,
    AuthDomainError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from src.services.user import User, UserRole, UserService

AUTH_PACKAGE_DIR = Path(__file__).resolve().parent.parent / "src" / "services" / "auth"
PASSWORD = "SecretPassword123"


@pytest_asyncio.fixture
async def user_service(db_session) -> UserService:
    return UserService.from_session(db_session)


@pytest_asyncio.fixture
async def auth_service(db_session) -> AuthService:
    return AuthService.from_session(db_session)


async def create_user(user_service: UserService, **overrides) -> User:
    payload = {
        "name": "Dosen ITK",
        "email": "dosen@itk.ac.id",
        "role": UserRole.INSTRUCTOR,
        "password_hash": hash_password(PASSWORD),
    }
    payload.update(overrides)
    return await user_service.create_user(**payload)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def test_password_hash_is_not_the_plain_text_password():
    digest = hash_password(PASSWORD)

    assert digest != PASSWORD
    assert digest.startswith("$2b$")
    assert PASSWORD not in digest


def test_password_verification_round_trip():
    digest = hash_password(PASSWORD)

    assert verify_password(PASSWORD, digest) is True
    assert verify_password("PasswordLain123", digest) is False


def test_verification_fails_without_stored_credential():
    assert verify_password(PASSWORD, None) is False
    assert verify_password(PASSWORD, "") is False


def test_verification_tolerates_unusable_stored_hash():
    assert verify_password(PASSWORD, "bukan-hash-bcrypt") is False


@pytest.mark.parametrize("password", ["pendek", "x" * 73])
def test_hashing_enforces_password_length_policy(password):
    with pytest.raises(ValueError):
        hash_password(password)


# ---------------------------------------------------------------------------
# Access token
# ---------------------------------------------------------------------------


def test_access_token_round_trip_returns_subject():
    user_id = uuid.uuid4()

    token = create_access_token(user_id)

    assert decode_access_token(token) == user_id


def test_expired_token_is_rejected():
    token = create_access_token(uuid.uuid4(), expires_delta=timedelta(seconds=-1))

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_token_signed_with_another_secret_is_rejected():
    foreign_token = jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "secret-yang-berbeda",
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(foreign_token)


@pytest.mark.parametrize(
    "token",
    [
        "bukan-token",
        "",
        "a.b.c",
        jwt.encode({"exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM),
        jwt.encode(
            {"sub": "bukan-uuid", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        ),
    ],
)
def test_unusable_token_is_rejected(token):
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_token_does_not_carry_trusted_role_claim():
    """Role bukan klaim token: hanya identifier user yang dibawa."""
    token = create_access_token(uuid.uuid4())

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

    assert set(payload) == {"sub", "iat", "exp"}


# ---------------------------------------------------------------------------
# Verifikasi kredensial
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valid_credentials_authenticate_the_user(auth_service, user_service):
    created = await create_user(user_service, role=UserRole.STUDENT)

    authenticated = await auth_service.authenticate(username="dosen@itk.ac.id", password=PASSWORD)

    assert authenticated.id == created.id
    assert authenticated.role is UserRole.STUDENT
    assert authenticated.can_authenticate() is True


@pytest.mark.asyncio
async def test_email_lookup_is_case_insensitive_at_login(auth_service, user_service):
    await create_user(user_service)

    authenticated = await auth_service.authenticate(username="DOSEN@ITK.AC.ID", password=PASSWORD)

    assert authenticated.email == "dosen@itk.ac.id"


@pytest.mark.asyncio
async def test_wrong_password_is_rejected(auth_service, user_service):
    await create_user(user_service)

    with pytest.raises(InvalidCredentialsError):
        await auth_service.authenticate(username="dosen@itk.ac.id", password="PasswordSalah123")


@pytest.mark.asyncio
async def test_unknown_email_is_rejected(auth_service):
    with pytest.raises(InvalidCredentialsError):
        await auth_service.authenticate(username="tidak-ada@itk.ac.id", password=PASSWORD)


@pytest.mark.asyncio
async def test_user_without_local_credential_cannot_login(auth_service, user_service):
    await create_user(user_service, password_hash=None)

    with pytest.raises(InvalidCredentialsError):
        await auth_service.authenticate(username="dosen@itk.ac.id", password=PASSWORD)


@pytest.mark.asyncio
async def test_inactive_user_is_rejected(auth_service, user_service):
    created = await create_user(user_service)
    await user_service.deactivate_user(created.id)

    with pytest.raises(InactiveUserError):
        await auth_service.authenticate(username="dosen@itk.ac.id", password=PASSWORD)


@pytest.mark.asyncio
async def test_all_authentication_failures_share_one_public_response(auth_service, user_service):
    """Response publik identik untuk semua penyebab: mencegah user enumeration."""
    await create_user(user_service, email="nonaktif@itk.ac.id")
    await user_service.deactivate_user((await user_service.get_user_by_email("nonaktif@itk.ac.id")).id)
    await create_user(user_service, email="tanpa-hash@itk.ac.id", password_hash=None)

    failures = []
    for username, password in (
        ("tidak-ada@itk.ac.id", PASSWORD),
        ("dosen@itk.ac.id", "PasswordSalah123"),
        ("nonaktif@itk.ac.id", PASSWORD),
        ("tanpa-hash@itk.ac.id", PASSWORD),
    ):
        with pytest.raises(AuthDomainError) as error:
            await auth_service.authenticate(username=username, password=password)
        failures.append((error.value.status_code, error.value.error_code, error.value.public_message))

    assert len(set(failures)) == 1


# ---------------------------------------------------------------------------
# Authentication state dan current user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_issued_token_resolves_back_to_the_user(auth_service, user_service):
    created = await create_user(user_service)

    token = await auth_service.issue_access_token(created)
    resolved = await auth_service.get_authenticated_user(token)

    assert resolved.id == created.id
    assert resolved.email == created.email


@pytest.mark.asyncio
async def test_token_is_not_issued_for_inactive_user(auth_service, user_service):
    created = await create_user(user_service)
    await user_service.deactivate_user(created.id)
    inactive = await user_service.get_user(created.id)

    with pytest.raises(InactiveUserError):
        await auth_service.issue_access_token(inactive)


@pytest.mark.asyncio
async def test_token_of_unknown_user_is_rejected(auth_service):
    token = create_access_token(uuid.uuid4())

    with pytest.raises(InvalidTokenError):
        await auth_service.get_authenticated_user(token)


@pytest.mark.asyncio
async def test_deactivation_invalidates_an_otherwise_valid_token(auth_service, user_service):
    created = await create_user(user_service)
    token = await auth_service.issue_access_token(created)

    await user_service.deactivate_user(created.id)

    with pytest.raises(InactiveUserError):
        await auth_service.get_authenticated_user(token)


@pytest.mark.asyncio
async def test_role_in_authenticated_identity_comes_from_the_user_record(auth_service, user_service):
    """Privilege mengikuti record User, bukan klaim di dalam token."""
    created = await create_user(user_service, role=UserRole.STUDENT)
    token = await auth_service.issue_access_token(created)

    await user_service.update_user(created.id, role=UserRole.INSTRUCTOR)

    assert (await auth_service.get_authenticated_user(token)).role is UserRole.INSTRUCTOR


# ---------------------------------------------------------------------------
# Batas layer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module_name", ["errors.py", "passwords.py", "tokens.py", "service.py"])
def test_auth_modules_do_not_import_http_moodle_or_llm(module_name):
    tree = ast.parse((AUTH_PACKAGE_DIR / module_name).read_text(encoding="utf-8"))

    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)

    # Identifier yang benar-benar dipakai di kode (bukan sekadar disebut di
    # docstring/komentar).
    identifiers = {
        node.id.lower() for node in ast.walk(tree) if isinstance(node, ast.Name)
    } | {node.attr.lower() for node in ast.walk(tree) if isinstance(node, ast.Attribute)}

    assert not any(module.split(".")[0] in {"fastapi", "starlette"} for module in modules)
    assert not any(module.startswith("src.routes") or module.startswith("src.controllers") for module in modules)
    assert not any(module.startswith("src.services.llm") for module in modules)
    assert not any("moodle" in identifier for identifier in identifiers)
    assert not any("llm" in identifier for identifier in identifiers)
