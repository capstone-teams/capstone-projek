"""Test User Repository & User Service (BE-03.2).

Pengujian memakai SQLite in-memory (lihat ``tests/conftest.py``) sehingga
lapisan ini dapat diverifikasi tanpa server PostgreSQL. Perilaku database
spesifik PostgreSQL diuji pada pengujian integrasi terpisah.

Field identity memakai nama atribut user Moodle (``username``, ``firstname``,
``lastname``, ``email``, ``password``); ``email`` tetap menjadi identity
attribute untuk login aplikasi.
"""

import ast
import shortuuid
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

from src.services.user import (
    DuplicateEmailError,
    DuplicateUsernameError,
    User,
    UserDomainError,
    UserNotFoundError,
    UserRepository,
    UserRole,
    UserService,
    UserStatus,
    UserValidationError,
)

BACKEND_DIR = Path(__file__).resolve().parent.parent
USER_PACKAGE_DIR = BACKEND_DIR / "src" / "services" / "user"
ROUTES_DIR = BACKEND_DIR / "src" / "routes"

APPLICATION_MODULES = ["mappers.py", "repository.py", "service.py"]
PASSWORD_HASH = "$2b$12$abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLM"


def missing_id() -> str:
    """Identifier berformat benar yang tidak mungkin ada di database."""
    return shortuuid.uuid()


@pytest_asyncio.fixture
async def repository(db_session) -> UserRepository:
    return UserRepository(db_session)


@pytest_asyncio.fixture
async def service(db_session) -> UserService:
    return UserService(UserRepository(db_session))


def imported_modules(path: Path) -> set[str]:
    """Nama modul yang diimpor sebuah file, dipakai untuk guard arsitektur."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def user_fields(**overrides: Any) -> dict[str, Any]:
    """Nilai identity valid sebagai basis setiap pembentukan user.

    ``users.username`` UNIQUE, sehingga username default diturunkan dari local
    part email: setiap user uji dengan email berbeda otomatis memakai username
    berbeda. Test yang memang menguji duplikat username mengisinya eksplisit.
    """
    payload: dict[str, Any] = {
        "firstname": "Dosen",
        "lastname": "ITK",
        "email": "dosen@itk.ac.id",
        "role": UserRole.INSTRUCTOR,
    }
    payload.update(overrides)
    payload.setdefault("username", payload["email"].split("@")[0])
    return payload


async def create_user(service: UserService, **overrides: Any):
    return await service.create_user(**user_fields(**overrides))


# ---------------------------------------------------------------------------
# Repository: operasi data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_persists_user_and_returns_persisted_state(repository):
    created = await repository.create(
        User.create(
            username="  dosen.itk  ",
            firstname="  Dosen  ",
            lastname="  ITK  ",
            email="Dosen@ITK.ac.id",
            role=UserRole.INSTRUCTOR,
        )
    )

    assert created.id is not None
    assert len(created.id) == 22
    assert created.username == "dosen.itk"
    assert created.firstname == "Dosen"
    assert created.lastname == "ITK"
    assert created.email == "dosen@itk.ac.id"
    assert created.status is UserStatus.ACTIVE
    assert created.created_at is not None
    assert created.updated_at is not None


@pytest.mark.asyncio
async def test_create_rejects_duplicate_email(repository, service):
    await create_user(service)

    with pytest.raises(DuplicateEmailError) as error:
        await repository.create(
            User.create(
                username="dosen.lain",
                firstname="Dosen",
                lastname="Lain",
                email="DOSEN@itk.ac.id",
                role=UserRole.STUDENT,
            )
        )

    assert error.value.email == "dosen@itk.ac.id"


@pytest.mark.asyncio
async def test_create_rejects_duplicate_username(repository, service):
    """Username adalah atribut Moodle dan kolom UNIQUE, jadi duplikatnya ditolak domain."""
    await create_user(service, username="dosen.itk")

    with pytest.raises(DuplicateUsernameError) as error:
        await repository.create(
            User.create(
                username="dosen.itk",
                firstname="Dosen",
                lastname="Lain",
                email="dosen.lain@itk.ac.id",
                role=UserRole.STUDENT,
            )
        )

    assert error.value.username == "dosen.itk"


@pytest.mark.asyncio
async def test_session_remains_usable_after_duplicate_identity(repository, service):
    await create_user(service)

    with pytest.raises(DuplicateEmailError):
        await create_user(service, username="dosen.lain", email="dosen@itk.ac.id")

    assert await repository.exists_by_email("dosen@itk.ac.id") is True


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing(repository):
    assert await repository.get_by_id(missing_id()) is None


@pytest.mark.asyncio
async def test_find_by_email_returns_none_when_missing(repository):
    assert await repository.find_by_email("tidak-ada@itk.ac.id") is None


@pytest.mark.asyncio
async def test_find_by_email_matches_case_insensitively(repository, service):
    created = await create_user(service)

    found = await repository.find_by_email("  DOSEN@ITK.AC.ID ")

    assert found is not None
    assert found.id == created.id


@pytest.mark.asyncio
async def test_exists_by_email_reflects_stored_identity(repository, service):
    assert await repository.exists_by_email("dosen@itk.ac.id") is False

    await create_user(service)

    assert await repository.exists_by_email("Dosen@ITK.ac.id") is True


@pytest.mark.asyncio
async def test_update_persists_changed_values(repository, service):
    created = await create_user(service)
    created.firstname = "Dosen Pembaruan"
    created.deactivate()

    updated = await repository.update(created)

    assert updated is not None
    assert updated.firstname == "Dosen Pembaruan"
    assert updated.status is UserStatus.INACTIVE
    assert (await repository.get_by_id(created.id)).firstname == "Dosen Pembaruan"


@pytest.mark.asyncio
async def test_update_returns_none_when_row_is_missing(repository):
    unsaved = User(
        id=missing_id(), **user_fields(username="hilang", email="hilang@itk.ac.id")
    )

    assert await repository.update(unsaved) is None


@pytest.mark.asyncio
async def test_update_requires_persisted_user(repository):
    unsaved = User(**user_fields(username="belum.ada", email="belum@itk.ac.id"))

    with pytest.raises(ValueError):
        await repository.update(unsaved)


@pytest.mark.asyncio
async def test_update_to_taken_email_is_rejected(repository, service):
    first = await create_user(service, email="pertama@itk.ac.id")
    second = await create_user(service, email="kedua@itk.ac.id")
    second.email = first.email

    with pytest.raises(DuplicateEmailError):
        await repository.update(second)


@pytest.mark.asyncio
async def test_update_to_taken_username_is_rejected(repository, service):
    first = await create_user(service, username="pertama", email="pertama@itk.ac.id")
    second = await create_user(service, username="kedua", email="kedua@itk.ac.id")
    second.username = first.username

    with pytest.raises(DuplicateUsernameError):
        await repository.update(second)


# ---------------------------------------------------------------------------
# Service: operasi aplikasi
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_user_returns_active_user_with_normalized_identity(service):
    created = await create_user(
        service, username="  dosen.itk  ", email="  DOSEN@ITK.AC.ID "
    )

    assert created.id is not None
    assert created.username == "dosen.itk"
    assert created.firstname == "Dosen"
    assert created.lastname == "ITK"
    assert created.email == "dosen@itk.ac.id"
    assert created.role is UserRole.INSTRUCTOR
    assert created.status is UserStatus.ACTIVE


@pytest.mark.asyncio
async def test_create_user_validates_domain_before_persistence(service):
    with pytest.raises(UserValidationError) as error:
        await service.create_user(**user_fields(username="   "))

    assert error.value.field == "username"
    assert await service.is_email_registered("dosen@itk.ac.id") is False


@pytest.mark.asyncio
async def test_create_user_rejects_arbitrary_role(service):
    with pytest.raises(UserValidationError) as error:
        await service.create_user(**user_fields(role="SUPERADMIN"))

    assert error.value.field == "role"


@pytest.mark.asyncio
async def test_create_user_rejects_duplicate_identity(service):
    await create_user(service)

    with pytest.raises(DuplicateEmailError):
        await create_user(service, username="dosen.lain")


@pytest.mark.asyncio
async def test_create_user_rejects_duplicate_username(service):
    await create_user(service, username="dosen.itk")

    with pytest.raises(DuplicateUsernameError):
        await create_user(service, username="dosen.itk", email="dosen.lain@itk.ac.id")


@pytest.mark.asyncio
async def test_get_user_returns_persisted_user(service):
    created = await create_user(service)

    found = await service.get_user(created.id)

    assert found.id == created.id
    assert found.email == created.email


@pytest.mark.asyncio
async def test_get_user_accepts_identifier_as_string(service):
    created = await create_user(service)

    assert (await service.get_user(str(created.id))).id == created.id


@pytest.mark.asyncio
async def test_get_user_rejects_invalid_identifier(service):
    with pytest.raises(UserValidationError) as error:
        await service.get_user("bukan-shortuuid")

    assert error.value.field == "id"


@pytest.mark.asyncio
async def test_get_user_rejects_uuid_shaped_identifier(service):
    """Identifier lama (UUID) bukan ShortUUID, sehingga ditolak sebelum query."""
    with pytest.raises(UserValidationError) as error:
        await service.get_user("3f2504e0-4f89-41d3-9a0c-0305e82c3301")

    assert error.value.field == "id"


@pytest.mark.asyncio
async def test_get_user_raises_consistent_not_found_error(service):
    unknown_id = missing_id()

    with pytest.raises(UserNotFoundError) as error:
        await service.get_user(unknown_id)

    assert error.value.identifier == unknown_id


@pytest.mark.asyncio
async def test_get_user_by_email_returns_user(service):
    created = await create_user(service)

    assert (await service.get_user_by_email("DOSEN@itk.ac.id")).id == created.id


@pytest.mark.asyncio
async def test_get_user_by_email_raises_same_not_found_error(service):
    with pytest.raises(UserNotFoundError) as error:
        await service.get_user_by_email("tidak-ada@itk.ac.id")

    assert error.value.identifier == "tidak-ada@itk.ac.id"
    assert isinstance(error.value, UserDomainError)


@pytest.mark.asyncio
async def test_find_user_by_email_returns_none_for_unknown_identity(service):
    assert await service.find_user_by_email("tidak-ada@itk.ac.id") is None


@pytest.mark.asyncio
async def test_find_user_by_id_returns_none_for_unknown_identifier(service):
    assert await service.find_user_by_id(missing_id()) is None


@pytest.mark.asyncio
async def test_update_user_changes_only_given_fields(service):
    created = await create_user(service, password=PASSWORD_HASH)

    updated = await service.update_user(
        created.id, firstname="Dosen Baru", role=UserRole.ADMIN
    )

    assert updated.firstname == "Dosen Baru"
    assert updated.role is UserRole.ADMIN
    assert updated.username == created.username
    assert updated.lastname == created.lastname
    assert updated.email == created.email
    assert updated.password == PASSWORD_HASH


@pytest.mark.asyncio
async def test_update_user_validates_role_before_persistence(service):
    created = await create_user(service, role=UserRole.INSTRUCTOR)

    with pytest.raises(UserValidationError) as error:
        await service.update_user(created.id, role="SUPERADMIN")

    assert error.value.field == "role"
    assert (await service.get_user(created.id)).role is UserRole.INSTRUCTOR


@pytest.mark.asyncio
async def test_update_user_validates_email_before_persistence(service):
    created = await create_user(service)

    with pytest.raises(UserValidationError) as error:
        await service.update_user(created.id, email="bukan-email")

    assert error.value.field == "email"
    assert (await service.get_user(created.id)).email == created.email


@pytest.mark.asyncio
async def test_update_user_validates_username_before_persistence(service):
    created = await create_user(service)

    with pytest.raises(UserValidationError) as error:
        await service.update_user(created.id, username="dosen itk")

    assert error.value.field == "username"
    assert (await service.get_user(created.id)).username == created.username


@pytest.mark.asyncio
async def test_update_user_rejects_taken_email(service):
    first = await create_user(service, username="pertama", email="pertama@itk.ac.id")
    second = await create_user(service, username="kedua", email="kedua@itk.ac.id")

    with pytest.raises(DuplicateEmailError):
        await service.update_user(second.id, email=first.email)

    assert (await service.get_user(second.id)).email == "kedua@itk.ac.id"


@pytest.mark.asyncio
async def test_update_user_rejects_taken_username(service):
    first = await create_user(service, username="pertama", email="pertama@itk.ac.id")
    second = await create_user(service, username="kedua", email="kedua@itk.ac.id")

    with pytest.raises(DuplicateUsernameError):
        await service.update_user(second.id, username=first.username)

    assert (await service.get_user(second.id)).username == "kedua"


@pytest.mark.asyncio
async def test_update_user_can_set_and_clear_password(service):
    created = await create_user(service)
    assert created.uses_local_authentication is False

    with_password = await service.update_user(created.id, password=PASSWORD_HASH)
    assert with_password.uses_local_authentication is True

    cleared = await service.update_user(created.id, password=None)
    assert cleared.password is None
    assert cleared.uses_local_authentication is False


@pytest.mark.asyncio
async def test_update_user_raises_not_found(service):
    with pytest.raises(UserNotFoundError):
        await service.update_user(missing_id(), firstname="Tidak Ada")


@pytest.mark.asyncio
async def test_deactivate_user_blocks_authentication_status(service):
    created = await create_user(service)

    deactivated = await service.deactivate_user(created.id)

    assert deactivated.status is UserStatus.INACTIVE
    assert deactivated.can_authenticate() is False
    assert (await service.get_user(created.id)).status is UserStatus.INACTIVE


@pytest.mark.asyncio
async def test_activate_user_restores_active_status(service):
    created = await create_user(service)
    await service.deactivate_user(created.id)

    activated = await service.activate_user(created.id)

    assert activated.status is UserStatus.ACTIVE
    assert activated.can_authenticate() is True


@pytest.mark.asyncio
async def test_deactivate_user_raises_not_found(service):
    with pytest.raises(UserNotFoundError):
        await service.deactivate_user(missing_id())


@pytest.mark.asyncio
async def test_get_user_role_reads_role_from_the_record(service):
    created = await create_user(service, role=UserRole.STUDENT)

    assert await service.get_user_role(created.id) is UserRole.STUDENT


@pytest.mark.asyncio
async def test_get_user_role_raises_not_found(service):
    with pytest.raises(UserNotFoundError):
        await service.get_user_role(missing_id())


@pytest.mark.asyncio
async def test_is_email_registered(service):
    assert await service.is_email_registered("dosen@itk.ac.id") is False

    await create_user(service)

    assert await service.is_email_registered("Dosen@ITK.ac.id") is True


@pytest.mark.asyncio
async def test_authentication_style_flow_needs_only_the_service(service):
    """Authentication (BE-03.3) cukup memakai service, tanpa query database langsung."""
    created = await create_user(service, role=UserRole.STUDENT)

    found = await service.find_user_by_email("DOSEN@ITK.AC.ID")

    assert found is not None
    assert found.id == created.id
    assert found.can_authenticate() is True
    assert await service.get_user_role(found.id) is UserRole.STUDENT


# ---------------------------------------------------------------------------
# Batas layer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module_name", APPLICATION_MODULES)
def test_application_layer_does_not_import_http_frameworks(module_name):
    modules = imported_modules(USER_PACKAGE_DIR / module_name)

    assert not any(module.split(".")[0] in {"fastapi", "starlette"} for module in modules)


@pytest.mark.parametrize("module_name", APPLICATION_MODULES)
def test_application_layer_has_no_moodle_or_llm_logic(module_name):
    path = USER_PACKAGE_DIR / module_name
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = imported_modules(path)

    # Identifier yang benar-benar dipakai di kode (bukan sekadar disebut di
    # docstring/komentar).
    identifiers = {
        node.id.lower() for node in ast.walk(tree) if isinstance(node, ast.Name)
    } | {node.attr.lower() for node in ast.walk(tree) if isinstance(node, ast.Attribute)}

    assert not any("moodle" in identifier for identifier in identifiers)
    assert not any("llm" in identifier for identifier in identifiers)
    assert not any(module.startswith("src.services.llm") for module in modules)


def test_repository_does_not_depend_on_the_service_module():
    """Data access tidak boleh bergantung pada operasi aplikasi (arah satu turun)."""
    modules = imported_modules(USER_PACKAGE_DIR / "repository.py")

    assert "src.services.user.service" not in modules


def test_routes_do_not_access_the_database_directly():
    """Router hanya urusan HTTP: tanpa SQLAlchemy, ORM model, maupun repository."""
    offenders = {}
    for path in sorted(ROUTES_DIR.glob("*.py")):
        forbidden = [
            module
            for module in imported_modules(path)
            if module.split(".")[0] == "sqlalchemy"
            or module.startswith("src.models")
            or module.startswith("src.services.user.repository")
        ]
        if forbidden:
            offenders[path.name] = forbidden

    assert offenders == {}
