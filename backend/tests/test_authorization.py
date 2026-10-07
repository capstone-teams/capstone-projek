"""Test role authorization mechanism (BE-03.4) pada database test (``conftest.db_session``).

Cakupan:

- keputusan :class:`RolePolicy` sebagai logika murni: single-role restriction,
  multiple-role restriction, role tidak dikenal, dan policy kosong;
- konfigurasi ``require_roles``: salah konfigurasi gagal saat didefinisikan,
  input role dinormalisasi;
- penegakan policy pada endpoint melalui ``require_roles`` — termasuk endpoint
  uji tambahan yang membuktikan guard yang sama dapat dipasang di lebih dari
  satu endpoint tanpa duplikasi pengecekan role;
- matriks role x endpoint, sehingga setiap kombinasi eksplisit;
- pemisahan authentication dan authorization: 401 untuk request tanpa
  authentication, 403 ``AUTHORIZATION_DENIED`` untuk role yang tidak sesuai;
- urutan guard: authentication dan authorization selesai sebelum validasi path
  dan sebelum handler dijalankan;
- role **selalu** berasal dari record User: payload/query/header/klaim token yang
  dikirim client tidak dapat menaikkan privilege.

Router ``/api/v1/testing/*`` hanya di-include pada fixture ``client`` di file
ini; endpoint tersebut bukan bagian dari aplikasi produksi.
"""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import jwt
import pytest
import pytest_asyncio
import shortuuid
from fastapi import APIRouter, Depends

from src.config.settings import settings
from src.main import create_app
from src.services.auth import RolePolicy, create_access_token, hash_password
from src.services.auth.errors import AuthorizationError, AuthorizationPolicyError
from src.services.dependencies import get_db_session, require_roles
from src.services.user import UserRole, UserService
from src.services.user.domain import User

AUTHORIZATION_MODULE = Path(__file__).parent.parent / "src/services/auth/authorization.py"

PASSWORD = "SecretPassword123"

INSTRUCTOR_ONLY_URL = "/api/v1/testing/instructor-only"
MULTI_ROLE_URL = "/api/v1/testing/multi-role"
SIDE_EFFECT_URL = "/api/v1/testing/side-effect"
LOWERCASE_ROLE_URL = "/api/v1/testing/lowercase-role"
ADMIN_USERS_URL = "/api/v1/admin/users"

# Endpoint uji: guard yang sama dipasang di beberapa endpoint berbeda, sehingga
# reusable-nya mekanisme terbukti tanpa mengubah router produksi.
instructor_only_router = APIRouter(prefix="/api/v1/testing/instructor-only", tags=["Testing"])
multi_role_router = APIRouter(prefix="/api/v1/testing/multi-role", tags=["Testing"])
side_effect_router = APIRouter(prefix="/api/v1/testing/side-effect", tags=["Testing"])
lowercase_role_router = APIRouter(prefix="/api/v1/testing/lowercase-role", tags=["Testing"])

# Mencatat eksekusi handler, dipakai untuk membuktikan authorization selesai
# sebelum business operation dijalankan. Dibersihkan oleh fixture autouse.
handler_calls: list[str] = []


@instructor_only_router.get("")
async def instructor_only_operation(
    current_user: User = Depends(require_roles(UserRole.INSTRUCTOR)),
) -> dict[str, str]:
    """Operation yang hanya boleh dijalankan INSTRUCTOR."""
    handler_calls.append(str(current_user.id))
    return {"operation": "instructor-only", "user": str(current_user.id)}


@multi_role_router.get("")
async def multi_role_operation(
    current_user: User = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.STUDENT)),
) -> dict[str, str]:
    """Operation dengan multiple-role restriction."""
    handler_calls.append(str(current_user.id))
    return {"operation": "instructor-or-student", "user": str(current_user.id)}


@side_effect_router.get("")
async def operation_with_side_effect(
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> dict[str, str]:
    """Operation ADMIN-only yang mencatat eksekusinya."""
    handler_calls.append(str(current_user.id))
    return {"operation": "admin-only", "user": str(current_user.id)}


@lowercase_role_router.get("")
async def lowercase_role_operation(
    current_user: User = Depends(require_roles("admin")),
) -> dict[str, str]:
    """Role ditulis dengan huruf kecil: harus dinormalisasi."""
    handler_calls.append(str(current_user.id))
    return {"operation": "lowercase-role", "user": str(current_user.id)}


@pytest.fixture(autouse=True)
def reset_handler_calls():
    """Pastikan catatan eksekusi handler tidak bocor antar test."""
    handler_calls.clear()
    yield
    handler_calls.clear()


@pytest_asyncio.fixture
async def client(db_session) -> httpx.AsyncClient:
    """Client HTTP ke aplikasi dengan session database test."""
    application = create_app()
    application.include_router(instructor_only_router)
    application.include_router(multi_role_router)
    application.include_router(side_effect_router)
    application.include_router(lowercase_role_router)

    async def override_get_db_session():
        yield db_session

    application.dependency_overrides[get_db_session] = override_get_db_session
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def user_service(db_session) -> UserService:
    return UserService.from_session(db_session)


async def create_user(user_service: UserService, *, role: UserRole, email: str) -> User:
    return await user_service.create_user(
        username=email.split("@")[0],
        firstname="Pengguna",
        lastname="Uji",
        email=email,
        role=role,
        password=hash_password(PASSWORD),
    )


def bearer(user: User) -> dict[str, str]:
    """Header Authorization dengan access token asli milik user."""
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _imported_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def _domain_user(role: UserRole, email: str) -> User:
    return User.create(
        username=email.split("@")[0],
        firstname="Pengguna",
        lastname="Uji",
        email=email,
        role=role,
    )


# ---------------------------------------------------------------------------
# RolePolicy (logika murni)
# ---------------------------------------------------------------------------


def test_policy_allows_the_configured_role_only():
    """Single-role restriction: hanya role yang dikonfigurasi yang diizinkan."""
    policy = RolePolicy.for_roles(UserRole.ADMIN)

    assert policy.allows(UserRole.ADMIN) is True
    assert policy.allows(UserRole.INSTRUCTOR) is False
    assert policy.allows(UserRole.STUDENT) is False


def test_policy_supports_multiple_roles():
    policy = RolePolicy.for_roles(UserRole.INSTRUCTOR, UserRole.STUDENT)

    assert policy.allows(UserRole.INSTRUCTOR) is True
    assert policy.allows(UserRole.STUDENT) is True
    assert policy.allows(UserRole.ADMIN) is False


def test_policy_normalizes_role_input_and_removes_duplicates():
    policy = RolePolicy.for_roles("admin", UserRole.ADMIN, "ADMIN")

    assert policy.roles == frozenset({UserRole.ADMIN})
    assert policy.roles <= set(UserRole)
    assert policy.allows("admin") is True


@pytest.mark.parametrize(
    "roles",
    [
        (),
        ("SUPERADMIN",),
        (UserRole.ADMIN, "SUPERADMIN"),
        (None,),
    ],
)
def test_policy_rejects_a_misconfigured_role_list(roles):
    """Policy salah tulis gagal saat didefinisikan, bukan lewat 403 saat runtime."""
    with pytest.raises(AuthorizationPolicyError):
        RolePolicy.for_roles(*roles)


@pytest.mark.parametrize("unknown_role", ["SUPERADMIN", "", None, 1])
def test_policy_never_allows_an_unknown_role(unknown_role):
    """Role di luar enum tidak boleh lolos: ditolak (False) atau error policy yang jelas."""
    policy = RolePolicy.for_roles(UserRole.ADMIN, UserRole.INSTRUCTOR, UserRole.STUDENT)

    try:
        decision = policy.allows(unknown_role)
    except (AuthorizationPolicyError, ValueError, TypeError):
        return

    assert decision is False


def test_policy_reads_the_role_from_the_user_record():
    policy = RolePolicy.for_roles(UserRole.INSTRUCTOR)

    assert policy.allows_user(_domain_user(UserRole.INSTRUCTOR, "dosen@itk.ac.id")) is True
    assert policy.allows_user(_domain_user(UserRole.STUDENT, "mhs@itk.ac.id")) is False


def test_enforce_returns_the_authorized_user():
    policy = RolePolicy.for_roles(UserRole.ADMIN)
    admin = _domain_user(UserRole.ADMIN, "admin@itk.ac.id")

    assert policy.enforce(admin) is admin


def test_enforce_reports_a_denied_operation_as_403_authorization_denied():
    policy = RolePolicy.for_roles(UserRole.ADMIN)

    with pytest.raises(AuthorizationError) as excinfo:
        policy.enforce(_domain_user(UserRole.STUDENT, "mhs@itk.ac.id"))

    error = excinfo.value
    assert error.error_code == "AUTHORIZATION_DENIED"
    assert error.status_code == 403
    # 403 bukan kegagalan authentication, jadi tidak membawa challenge header.
    assert error.challenge is False
    assert error.required_roles == (UserRole.ADMIN,)


def test_policy_module_stays_free_of_http_and_database_dependencies():
    """Keputusan authorization harus dapat diuji tanpa framework/infrastruktur."""
    assert _imported_roots(AUTHORIZATION_MODULE).isdisjoint({"fastapi", "starlette", "sqlalchemy"})


# ---------------------------------------------------------------------------
# require_roles (konfigurasi guard)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "roles",
    [
        (),
        ("SUPERADMIN",),
        (UserRole.ADMIN, "SUPERADMIN"),
        (None,),
    ],
)
def test_require_roles_rejects_a_misconfigured_role_list_at_definition_time(roles):
    """Guard salah konfigurasi gagal saat didefinisikan, bukan saat request."""
    with pytest.raises(AuthorizationPolicyError):
        require_roles(*roles)


@pytest.mark.asyncio
async def test_require_roles_normalizes_lowercase_role_names(client, user_service):
    admin = await create_user(user_service, role=UserRole.ADMIN, email="admin@itk.ac.id")
    instructor = await create_user(user_service, role=UserRole.INSTRUCTOR, email="dosen@itk.ac.id")

    allowed = await client.get(LOWERCASE_ROLE_URL, headers=bearer(admin))
    denied = await client.get(LOWERCASE_ROLE_URL, headers=bearer(instructor))

    assert allowed.status_code == 200
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "AUTHORIZATION_DENIED"


# ---------------------------------------------------------------------------
# Penegakan policy pada endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_instructor_only_endpoint_allows_instructor(client, user_service):
    instructor = await create_user(user_service, role=UserRole.INSTRUCTOR, email="dosen@itk.ac.id")

    response = await client.get(INSTRUCTOR_ONLY_URL, headers=bearer(instructor))

    assert response.status_code == 200
    # Identitas yang sudah diotorisasi diteruskan ke handler.
    assert response.json() == {"operation": "instructor-only", "user": str(instructor.id)}


@pytest.mark.asyncio
async def test_instructor_only_endpoint_rejects_student(client, user_service):
    student = await create_user(user_service, role=UserRole.STUDENT, email="mhs@itk.ac.id")

    response = await client.get(INSTRUCTOR_ONLY_URL, headers=bearer(student))

    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "AUTHORIZATION_DENIED",
            "message": "Akses ditolak.",
            "details": [],
        }
    }
    # Role apa yang dibutuhkan tidak diungkap, dan tidak ada challenge header.
    assert "INSTRUCTOR" not in response.text
    assert "www-authenticate" not in response.headers


@pytest.mark.asyncio
async def test_single_role_policy_rejects_every_other_role(client, user_service):
    """ADMIN pun tidak otomatis boleh: single-role restriction bersifat eksplisit."""
    admin = await create_user(user_service, role=UserRole.ADMIN, email="admin@itk.ac.id")

    response = await client.get(INSTRUCTOR_ONLY_URL, headers=bearer(admin))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTHORIZATION_DENIED"


@pytest.mark.asyncio
async def test_multiple_role_policy_allows_each_configured_role(client, user_service):
    instructor = await create_user(user_service, role=UserRole.INSTRUCTOR, email="dosen@itk.ac.id")
    student = await create_user(user_service, role=UserRole.STUDENT, email="mhs@itk.ac.id")
    admin = await create_user(user_service, role=UserRole.ADMIN, email="admin@itk.ac.id")

    responses = [
        await client.get(MULTI_ROLE_URL, headers=bearer(instructor)),
        await client.get(MULTI_ROLE_URL, headers=bearer(student)),
        await client.get(MULTI_ROLE_URL, headers=bearer(admin)),
    ]

    assert [response.status_code for response in responses] == [200, 200, 403]
    assert responses[0].json()["user"] == str(instructor.id)
    assert responses[1].json()["user"] == str(student.id)


# ---------------------------------------------------------------------------
# Matriks role x endpoint
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url, allowed_roles",
    [
        (INSTRUCTOR_ONLY_URL, {UserRole.INSTRUCTOR}),
        (MULTI_ROLE_URL, {UserRole.INSTRUCTOR, UserRole.STUDENT}),
        (SIDE_EFFECT_URL, {UserRole.ADMIN}),
        (LOWERCASE_ROLE_URL, {UserRole.ADMIN}),
    ],
)
@pytest.mark.parametrize("role", list(UserRole))
@pytest.mark.asyncio
async def test_role_endpoint_matrix(client, user_service, url, allowed_roles, role):
    """Setiap kombinasi role x endpoint eksplisit: diizinkan hanya bila role terdaftar."""
    user = await create_user(user_service, role=role, email=f"{role.value.lower()}@itk.ac.id")

    response = await client.get(url, headers=bearer(user))

    if role in allowed_roles:
        assert response.status_code == 200
        assert response.json()["user"] == str(user.id)
        assert handler_calls == [str(user.id)]
    else:
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_DENIED"
        assert handler_calls == []


# ---------------------------------------------------------------------------
# Authentication vs authorization (401 vs 403)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthenticated_request_is_rejected_before_authorization(client):
    response = await client.get(INSTRUCTOR_ONLY_URL)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_request_with_an_invalid_token_never_reaches_authorization(client):
    response = await client.get(
        INSTRUCTOR_ONLY_URL, headers={"Authorization": "Bearer bukan-token"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_expired_token_fails_authentication_not_authorization(client, user_service):
    instructor = await create_user(user_service, role=UserRole.INSTRUCTOR, email="dosen@itk.ac.id")
    expired = create_access_token(instructor.id, expires_delta=timedelta(seconds=-1))

    response = await client.get(INSTRUCTOR_ONLY_URL, headers={"Authorization": f"Bearer {expired}"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_valid_token_of_an_unknown_user_fails_authentication(client):
    """Token sah untuk user yang tidak ada: 401, bukan 403 atau 500."""
    orphan_token = create_access_token(shortuuid.uuid())

    responses = [
        await client.get(url, headers={"Authorization": f"Bearer {orphan_token}"})
        for url in (INSTRUCTOR_ONLY_URL, MULTI_ROLE_URL, SIDE_EFFECT_URL, ADMIN_USERS_URL)
    ]

    assert [response.status_code for response in responses] == [401, 401, 401, 401]
    assert {response.json()["error"]["code"] for response in responses} == {"AUTHENTICATION_FAILED"}
    assert handler_calls == []


@pytest.mark.asyncio
async def test_deactivated_user_fails_authentication_not_authorization(client, user_service):
    """Deaktivasi ditangani authentication, sehingga hasilnya 401 (bukan 403)."""
    instructor = await create_user(user_service, role=UserRole.INSTRUCTOR, email="dosen@itk.ac.id")
    headers = bearer(instructor)

    await user_service.deactivate_user(instructor.id)
    response = await client.get(INSTRUCTOR_ONLY_URL, headers=headers)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


# ---------------------------------------------------------------------------
# Handler tidak dijalankan tanpa authorization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_denied_request_never_runs_the_protected_operation(client, user_service):
    student = await create_user(user_service, role=UserRole.STUDENT, email="mhs@itk.ac.id")

    response = await client.get(SIDE_EFFECT_URL, headers=bearer(student))

    assert response.status_code == 403
    assert handler_calls == []


@pytest.mark.asyncio
async def test_unauthenticated_request_never_runs_the_protected_operation(client):
    responses = [
        await client.get(SIDE_EFFECT_URL),
        await client.get(SIDE_EFFECT_URL, headers={"Authorization": "Bearer bukan-token"}),
        await client.get(SIDE_EFFECT_URL, headers={"Authorization": "Basic ZG9zZW46cGFzcw=="}),
    ]

    assert [response.status_code for response in responses] == [401, 401, 401]
    assert handler_calls == []


@pytest.mark.asyncio
async def test_authorized_request_runs_the_protected_operation_exactly_once(client, user_service):
    admin = await create_user(user_service, role=UserRole.ADMIN, email="admin@itk.ac.id")

    response = await client.get(SIDE_EFFECT_URL, headers=bearer(admin))

    assert response.status_code == 200
    assert handler_calls == [str(admin.id)]


# ---------------------------------------------------------------------------
# Urutan guard terhadap validasi path (endpoint admin)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("role", [UserRole.INSTRUCTOR, UserRole.STUDENT])
@pytest.mark.parametrize(
    "malformed_id",
    ["bukan-id", "1234567890123456789012", "3f2504e0-4f89-41d3-9a0c-0305e82c3301"],
)
@pytest.mark.asyncio
async def test_non_admin_gets_403_before_path_validation(client, user_service, role, malformed_id):
    """Guard dijalankan sebelum validasi path: bentuk ID tidak bocor ke non-admin."""
    user = await create_user(user_service, role=role, email="lain@itk.ac.id")

    response = await client.get(f"{ADMIN_USERS_URL}/{malformed_id}", headers=bearer(user))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTHORIZATION_DENIED"


@pytest.mark.parametrize(
    "malformed_id",
    ["bukan-id", "1234567890123456789012", "3f2504e0-4f89-41d3-9a0c-0305e82c3301"],
)
@pytest.mark.asyncio
async def test_unauthenticated_gets_401_before_path_validation(client, malformed_id):
    response = await client.get(f"{ADMIN_USERS_URL}/{malformed_id}")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_admin_still_gets_validation_error_for_a_malformed_identifier(client, user_service):
    """Setelah lolos guard, validasi path berlaku normal: 422 untuk ID salah bentuk."""
    admin = await create_user(user_service, role=UserRole.ADMIN, email="admin@itk.ac.id")

    response = await client.get(f"{ADMIN_USERS_URL}/bukan-id", headers=bearer(admin))

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Role berasal dari record User, bukan dari client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_client_supplied_role_cannot_raise_privilege(client, user_service):
    """Role pada body, query, dan header tidak dipercaya sama sekali."""
    student = await create_user(user_service, role=UserRole.STUDENT, email="mhs@itk.ac.id")
    headers = {
        **bearer(student),
        "X-Role": "ADMIN",
        "X-User-Role": "INSTRUCTOR",
    }

    responses = [
        await client.get(
            INSTRUCTOR_ONLY_URL,
            headers=headers,
            params={"role": "ADMIN", "role_override": "INSTRUCTOR"},
        ),
        await client.request(
            "GET",
            INSTRUCTOR_ONLY_URL,
            headers=headers,
            json={"role": "ADMIN", "roles": ["INSTRUCTOR"]},
        ),
    ]

    assert [response.status_code for response in responses] == [403, 403]
    assert {response.json()["error"]["code"] for response in responses} == {"AUTHORIZATION_DENIED"}
    assert handler_calls == []


@pytest.mark.asyncio
async def test_role_claim_signed_in_the_token_is_ignored(client, user_service):
    """Klaim role pada token (ditandatangani SECRET_KEY asli) tetap tidak dipakai."""
    student = await create_user(user_service, role=UserRole.STUDENT, email="mhs@itk.ac.id")
    issued = datetime.now(timezone.utc)
    forged = jwt.encode(
        {
            "sub": str(student.id),
            "role": "INSTRUCTOR",
            "roles": ["INSTRUCTOR", "ADMIN"],
            "iat": int(issued.timestamp()),
            "exp": int((issued + timedelta(minutes=30)).timestamp()),
        },
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    response = await client.get(INSTRUCTOR_ONLY_URL, headers={"Authorization": f"Bearer {forged}"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTHORIZATION_DENIED"


@pytest.mark.asyncio
async def test_role_change_takes_effect_without_a_new_token(client, user_service):
    """Role dibaca ulang dari record User setiap request."""
    user = await create_user(user_service, role=UserRole.STUDENT, email="mhs@itk.ac.id")
    headers = bearer(user)

    assert (await client.get(INSTRUCTOR_ONLY_URL, headers=headers)).status_code == 403

    await user_service.update_user(user.id, role=UserRole.INSTRUCTOR)
    assert (await client.get(INSTRUCTOR_ONLY_URL, headers=headers)).status_code == 200

    await user_service.update_user(user.id, role=UserRole.STUDENT)
    assert (await client.get(INSTRUCTOR_ONLY_URL, headers=headers)).status_code == 403


# ---------------------------------------------------------------------------
# Konsistensi kontrak kegagalan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_guarded_endpoints_deny_with_the_same_response(client, user_service):
    """Guard yang sama menghasilkan kontrak kegagalan yang konsisten di endpoint berbeda."""
    student = await create_user(user_service, role=UserRole.STUDENT, email="mhs@itk.ac.id")
    headers = bearer(student)

    responses = [
        await client.get(INSTRUCTOR_ONLY_URL, headers=headers),
        await client.get(SIDE_EFFECT_URL, headers=headers),
        await client.get(ADMIN_USERS_URL, headers=headers),
    ]

    assert [response.status_code for response in responses] == [403, 403, 403]
    assert len({response.text for response in responses}) == 1


@pytest.mark.asyncio
async def test_unauthenticated_guarded_endpoints_fail_with_the_same_response(client):
    responses = [
        await client.get(INSTRUCTOR_ONLY_URL),
        await client.get(SIDE_EFFECT_URL),
        await client.get(ADMIN_USERS_URL),
    ]

    assert [response.status_code for response in responses] == [401, 401, 401]
    assert len({response.text for response in responses}) == 1
