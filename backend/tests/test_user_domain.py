"""Test domain User dan Role (BE-03.1).

Domain model diuji tanpa database dan tanpa HTTP layer: seluruh aturan identity,
role, status, dan lifecycle harus dapat diverifikasi sebagai pure Python.
"""

import ast
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.models.user import User as UserEntity
from src.models.user import UserRole as OrmUserRole
from src.models.user import UserStatus as OrmUserStatus
from src.services.user import (
    MAX_EMAIL_LENGTH,
    MAX_NAME_LENGTH,
    User,
    UserDomainError,
    UserRole,
    UserStatus,
    UserValidationError,
)
from src.services.user import enums as domain_enums

USER_PACKAGE_DIR = Path(__file__).resolve().parent.parent / "src" / "services" / "user"

FORBIDDEN_IMPORT_ROOTS = {"fastapi", "starlette"}


def build_user(**overrides) -> User:
    """User valid dengan nilai default, dipakai sebagai basis tiap test."""
    payload = {
        "name": "Dosen ITK",
        "email": "dosen@itk.ac.id",
        "role": UserRole.INSTRUCTOR,
    }
    payload.update(overrides)
    return User(**payload)


# ---------------------------------------------------------------------------
# Representasi role dan status
# ---------------------------------------------------------------------------


def test_role_values_are_exactly_the_application_roles():
    assert {role.value for role in UserRole} == {"INSTRUCTOR", "STUDENT", "ADMIN"}


def test_status_values_are_defined():
    assert {status.value for status in UserStatus} == {"ACTIVE", "INACTIVE"}


def test_domain_enums_are_the_single_source_from_models():
    """Domain me-reuse enum BE-02, bukan mendefinisikan nilai baru."""
    assert domain_enums.UserRole is OrmUserRole
    assert domain_enums.UserStatus is OrmUserStatus
    assert UserRole.INSTRUCTOR is OrmUserRole.INSTRUCTOR
    assert UserStatus.ACTIVE is OrmUserStatus.ACTIVE


# ---------------------------------------------------------------------------
# Pembentukan user dan normalisasi
# ---------------------------------------------------------------------------


def test_create_builds_active_user_without_identifier_or_timestamps():
    user = User.create(name="Dosen ITK", email="dosen@itk.ac.id", role="instructor")

    assert user.id is None
    assert user.created_at is None
    assert user.updated_at is None
    assert user.status is UserStatus.ACTIVE
    assert user.role is UserRole.INSTRUCTOR
    assert user.password_hash is None


def test_identity_values_are_normalized():
    user = build_user(name="  Dosen ITK  ", email="  DOSEN@ITK.AC.ID ")

    assert user.name == "Dosen ITK"
    assert user.email == "dosen@itk.ac.id"


def test_case_insensitive_identity_does_not_create_distinct_users():
    first = build_user(email="Dosen@ITK.ac.id")
    second = build_user(email="dosen@itk.ac.id")

    assert first.email == second.email


@pytest.mark.parametrize("role_value", ["instructor", "Instructor", "INSTRUCTOR", UserRole.INSTRUCTOR])
def test_role_accepts_enum_and_case_insensitive_string(role_value):
    user = build_user(role=role_value)

    assert user.role is UserRole.INSTRUCTOR


@pytest.mark.parametrize("status_value", ["active", "Active", UserStatus.ACTIVE])
def test_status_accepts_enum_and_case_insensitive_string(status_value):
    user = build_user(status=status_value)

    assert user.status is UserStatus.ACTIVE


def test_lifecycle_metadata_from_persistence_is_accepted():
    user_id = uuid.uuid4()
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    user = build_user(id=str(user_id), created_at=created_at, updated_at=created_at)

    assert user.id == user_id
    assert user.created_at == created_at


# ---------------------------------------------------------------------------
# Validasi identity field
# ---------------------------------------------------------------------------


def test_name_at_maximum_length_is_accepted():
    user = build_user(name="a" * MAX_NAME_LENGTH)

    assert len(user.name) == MAX_NAME_LENGTH


@pytest.mark.parametrize("invalid_name", ["", "   ", "\t", None, 123, ["Dosen"]])
def test_invalid_name_is_rejected(invalid_name):
    with pytest.raises(UserValidationError) as error:
        build_user(name=invalid_name)

    assert error.value.field == "name"


def test_name_over_maximum_length_is_rejected():
    with pytest.raises(UserValidationError):
        build_user(name="a" * (MAX_NAME_LENGTH + 1))


def test_name_with_control_characters_is_rejected():
    with pytest.raises(UserValidationError):
        build_user(name="Dosen\nITK")


@pytest.mark.parametrize(
    "valid_email",
    [
        "dosen@itk.ac.id",
        "first.last@itk.ac.id",
        "dosen+capstone@itk.ac.id",
        "dosen@student.itk.ac.id",
        "d-osen_1@sub-domain.example.co",
    ],
)
def test_valid_email_is_accepted(valid_email):
    user = build_user(email=valid_email)

    assert user.email == valid_email


@pytest.mark.parametrize(
    "invalid_email",
    [
        "",
        "   ",
        "dosen",
        "dosen@",
        "@itk.ac.id",
        "dosen@itk",
        "dosen@itk.",
        "dosen itk@itk.ac.id",
        "dosen@@itk.ac.id",
        ".dosen@itk.ac.id",
        "dosen.@itk.ac.id",
        "do..sen@itk.ac.id",
        "dosen@-itk.ac.id",
        "dosen@itk.ac.id.",
        None,
        123,
    ],
)
def test_invalid_email_is_rejected(invalid_email):
    with pytest.raises(UserValidationError) as error:
        build_user(email=invalid_email)

    assert error.value.field == "email"


def test_email_over_maximum_length_is_rejected():
    too_long = f"{'a' * MAX_EMAIL_LENGTH}@itk.ac.id"

    with pytest.raises(UserValidationError):
        build_user(email=too_long)


# ---------------------------------------------------------------------------
# Role dan status tidak boleh berisi nilai arbitrary
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("arbitrary_role", ["SUPERADMIN", "superadmin", "", None, 1])
def test_arbitrary_role_is_rejected(arbitrary_role):
    with pytest.raises(UserValidationError) as error:
        build_user(role=arbitrary_role)

    assert error.value.field == "role"
    assert "INSTRUCTOR" in error.value.message


@pytest.mark.parametrize("arbitrary_status", ["DELETED", "PENDING", "", None, 1])
def test_arbitrary_status_is_rejected(arbitrary_status):
    with pytest.raises(UserValidationError) as error:
        build_user(status=arbitrary_status)

    assert error.value.field == "status"


def test_role_and_status_errors_are_domain_errors():
    with pytest.raises(UserDomainError):
        build_user(role="OWNER")


# ---------------------------------------------------------------------------
# Password hash hanya relevan untuk local authentication
# ---------------------------------------------------------------------------


def test_user_without_password_hash_does_not_use_local_authentication():
    user = build_user(password_hash=None)

    assert user.password_hash is None
    assert user.uses_local_authentication is False


def test_user_with_password_hash_uses_local_authentication():
    user = build_user(password_hash="$2b$12$abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLM")

    assert user.uses_local_authentication is True


@pytest.mark.parametrize("invalid_hash", ["", "   ", "PasswordSuperRahasia 123", "a" * 256, 123])
def test_invalid_password_hash_is_rejected(invalid_hash):
    with pytest.raises(UserValidationError) as error:
        build_user(password_hash=invalid_hash)

    assert error.value.field == "password_hash"


def test_user_representation_does_not_leak_password_hash():
    user = build_user(password_hash="$2b$12$secret-hash-value")

    assert "secret-hash-value" not in str(user)
    assert "secret-hash-value" not in repr(user)
    assert "password_hash=set" in repr(user)


# ---------------------------------------------------------------------------
# Aturan lifecycle
# ---------------------------------------------------------------------------


def test_new_user_is_active_and_may_authenticate():
    user = build_user()

    assert user.is_active is True
    assert user.can_authenticate() is True


def test_deactivated_user_may_not_authenticate():
    user = build_user()

    user.deactivate()

    assert user.status is UserStatus.INACTIVE
    assert user.is_active is False
    assert user.can_authenticate() is False


def test_deactivate_and_activate_are_idempotent():
    user = build_user()

    user.deactivate()
    user.deactivate()
    assert user.status is UserStatus.INACTIVE

    user.activate()
    user.activate()
    assert user.status is UserStatus.ACTIVE


def test_role_can_be_changed_within_defined_roles():
    user = build_user(role=UserRole.STUDENT)

    user.change_role("admin")

    assert user.role is UserRole.ADMIN


def test_role_cannot_be_changed_to_arbitrary_value():
    user = build_user()

    with pytest.raises(UserValidationError):
        user.change_role("SUPERADMIN")

    assert user.role is UserRole.INSTRUCTOR


# ---------------------------------------------------------------------------
# Batas domain vs persistence dan HTTP
# ---------------------------------------------------------------------------


def test_domain_model_does_not_duplicate_the_persistence_entity():
    assert User is not UserEntity
    assert not issubclass(User, UserEntity)


@pytest.mark.parametrize("field_name", ["moodle_user_id", "moodle_password", "moodle_token", "agent_id", "permissions"])
def test_domain_model_has_no_moodle_or_agent_fields(field_name):
    assert field_name not in User.__dataclass_fields__


def test_domain_package_does_not_import_http_frameworks():
    """Domain tidak boleh bergantung pada implementasi HTTP/API.

    Modul ORM boleh dirujuk karena enum role/status didefinisikan di sana,
    tetapi FastAPI/Starlette tidak boleh muncul di paket domain.
    """
    imported_roots = set()
    for module_path in USER_PACKAGE_DIR.glob("*.py"):
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])

    assert imported_roots.isdisjoint(FORBIDDEN_IMPORT_ROOTS), imported_roots
