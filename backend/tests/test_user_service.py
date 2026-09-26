"""Test User Repository & User Service (BE-03.2).

Pengujian memakai SQLite in-memory (lihat ``tests/conftest.py``) sehingga
lapisan ini dapat diverifikasi tanpa server PostgreSQL. Perilaku database
spesifik PostgreSQL diuji pada pengujian integrasi terpisah.
"""

import ast
import uuid
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

from src.services.user import (
    DuplicateEmailError,
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


async def create_user(service: UserService, **overrides: Any):
    payload: dict[str, Any] = {
        "name": "Dosen ITK",
        "email": "dosen@itk.ac.id",
        "role": UserRole.INSTRUCTOR,
    }
    payload.update(overrides)
    return await service.create_user(**payload)


# ---------------------------------------------------------------------------
# Repository: operasi data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_persists_user_and_returns_persisted_state(repository):
    created = await repository.create(
        User.create(name="  Dosen ITK  ", email="Dosen@ITK.ac.id", role=UserRole.INSTRUCTOR)
    )

    assert created.id is not None
    assert created.name == "Dosen ITK"
    assert created.email == "dosen@itk.ac.id"
    assert created.status is UserStatus.ACTIVE
    assert created.created_at is not None
    assert created.updated_at is not None


@pytest.mark.asyncio
async def test_create_rejects_duplicate_identity(repository, service):
    await create_user(service)

    with pytest.raises(DuplicateEmailError) as error:
        await repository.create(
            User.create(name="Dosen Lain", email="DOSEN@itk.ac.id", role=UserRole.STUDENT)
        )

    assert error.value.email == "dosen@itk.ac.id"


@pytest.mark.asyncio
async def test_session_remains_usable_after_duplicate_identity(repository, service):
    await create_user(service)

    with pytest.raises(DuplicateEmailError):
        await create_user(service, email="dosen@itk.ac.id")

    assert await repository.exists_by_email("dosen@itk.ac.id") is True


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing(repository):
    assert await repository.get_by_id(uuid.uuid4()) is None


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
    created.name = "Dosen Pembaruan"
    created.deactivate()

    updated = await repository.update(created)

    assert updated is not None
    assert updated.name == "Dosen Pembaruan"
    assert updated.status is UserStatus.INACTIVE
    assert (await repository.get_by_id(created.id)).name == "Dosen Pembaruan"


@pytest.mark.asyncio
async def test_update_returns_none_when_row_is_missing(repository):
    unsaved = User(id=uuid.uuid4(), name="Hilang", email="hilang@itk.ac.id", role=UserRole.ADMIN)

    assert await repository.update(unsaved) is None


@pytest.mark.asyncio
async def test_update_requires_persisted_user(repository):
    unsaved = User(name="Belum Ada", email="belum@itk.ac.id", role=UserRole.STUDENT)

    with pytest.raises(ValueError):
        await repository.update(unsaved)


@pytest.mark.asyncio
async def test_update_to_taken_email_is_rejected(repository, service):
    first = await create_user(service, email="pertama@itk.ac.id")
    second = await create_user(service, email="kedua@itk.ac.id")
    second.email = first.email

    with pytest.raises(DuplicateEmailError):
        await repository.update(second)


# ---------------------------------------------------------------------------
# Service: operasi aplikasi
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_user_returns_active_user_with_normalized_identity(service):
    created = await create_user(service, name="  Dosen ITK  ", email="  DOSEN@ITK.AC.ID ")

    assert created.id is not None
    assert created.name == "Dosen ITK"
    assert created.email == "dosen@itk.ac.id"
    assert created.role is UserRole.INSTRUCTOR
    assert created.status is UserStatus.ACTIVE


@pytest.mark.asyncio
async def test_create_user_validates_domain_before_persistence(service):
    with pytest.raises(UserValidationError) as error:
        await service.create_user(name="   ", email="dosen@itk.ac.id", role=UserRole.INSTRUCTOR)

    assert error.value.field == "name"
    assert await service.is_email_registered("dosen@itk.ac.id") is False


@pytest.mark.asyncio
async def test_create_user_rejects_arbitrary_role(service):
    with pytest.raises(UserValidationError) as error:
        await service.create_user(name="Dosen", email="dosen@itk.ac.id", role="SUPERADMIN")

    assert error.value.field == "role"


@pytest.mark.asyncio
async def test_create_user_rejects_duplicate_identity(service):
    await create_user(service)

    with pytest.raises(DuplicateEmailError):
        await create_user(service, name="Dosen Lain")


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
        await service.get_user("bukan-uuid")

    assert error.value.field == "id"


@pytest.mark.asyncio
async def test_get_user_raises_consistent_not_found_error(service):
    missing_id = uuid.uuid4()

    with pytest.raises(UserNotFoundError) as error:
        await service.get_user(missing_id)

    assert error.value.identifier == missing_id


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
    assert await service.find_user_by_id(uuid.uuid4()) is None


@pytest.mark.asyncio
async def test_update_user_changes_only_given_fields(service):
    created = await create_user(service, password_hash=PASSWORD_HASH)

    updated = await service.update_user(created.id, name="Dosen Baru", role=UserRole.ADMIN)

    assert updated.name == "Dosen Baru"
    assert updated.role is UserRole.ADMIN
    assert updated.email == created.email
    assert updated.password_hash == PASSWORD_HASH


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
async def test_update_user_rejects_taken_email(service):
    first = await create_user(service, email="pertama@itk.ac.id")
    second = await create_user(service, email="kedua@itk.ac.id")

    with pytest.raises(DuplicateEmailError):
        await service.update_user(second.id, email=first.email)

    assert (await service.get_user(second.id)).email == "kedua@itk.ac.id"


@pytest.mark.asyncio
async def test_update_user_can_set_and_clear_password_hash(service):
    created = await create_user(service)
    assert created.uses_local_authentication is False

    with_hash = await service.update_user(created.id, password_hash=PASSWORD_HASH)
    assert with_hash.uses_local_authentication is True

    cleared = await service.update_user(created.id, password_hash=None)
    assert cleared.password_hash is None
    assert cleared.uses_local_authentication is False


@pytest.mark.asyncio
async def test_update_user_raises_not_found(service):
    missing_id = uuid.uuid4()

    with pytest.raises(UserNotFoundError):
        await service.update_user(missing_id, name="Tidak Ada")


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
        await service.deactivate_user(uuid.uuid4())


@pytest.mark.asyncio
async def test_get_user_role_reads_role_from_the_record(service):
    created = await create_user(service, role=UserRole.STUDENT)

    assert await service.get_user_role(created.id) is UserRole.STUDENT


@pytest.mark.asyncio
async def test_get_user_role_raises_not_found(service):
    with pytest.raises(UserNotFoundError):
        await service.get_user_role(uuid.uuid4())


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
