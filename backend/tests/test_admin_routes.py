"""Test endpoint administrasi (BE-03.4) pada SQLite in-memory.

Endpoint diuji melalui ASGI app (httpx ASGITransport) dengan dependency override
ke session test, sehingga kombinasi authentication → authorization → business
operation benar-benar terverifikasi: ADMIN diizinkan, role lain 403
``AUTHORIZATION_DENIED``, request tanpa authentication 401
``AUTHENTICATION_FAILED``, dan response tidak pernah memuat credential.
"""

from __future__ import annotations

import uuid

import httpx
import pytest
import pytest_asyncio

from src.main import create_app
from src.services.auth import hash_password
from src.services.dependencies import get_db_session
from src.services.user import UserRole, UserService

PASSWORD = "SecretPassword123"
ADMIN_USERS_URL = "/api/v1/admin/users"


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


@pytest_asyncio.fixture
async def user_service(db_session) -> UserService:
    return UserService.from_session(db_session)


async def create_user(user_service: UserService, **overrides):
    payload = {
        "name": "Pengguna Uji",
        "email": "admin@itk.ac.id",
        "role": UserRole.ADMIN,
        "password_hash": hash_password(PASSWORD),
    }
    payload.update(overrides)
    return await user_service.create_user(**payload)


async def login(client: httpx.AsyncClient, *, username: str = "admin@itk.ac.id") -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_admin_can_list_users(client, user_service):
    await create_user(user_service)
    await create_user(user_service, name="Dosen ITK", email="dosen@itk.ac.id", role=UserRole.INSTRUCTOR)
    await create_user(
        user_service, name="Mahasiswa ITK", email="mhs@itk.ac.id", role=UserRole.STUDENT
    )

    response = await client.get(ADMIN_USERS_URL, headers=await login(client))

    assert response.status_code == 200
    users = response.json()["users"]
    # Seluruh user dikembalikan, diurutkan berdasarkan email (deterministik).
    assert [user["email"] for user in users] == [
        "admin@itk.ac.id",
        "dosen@itk.ac.id",
        "mhs@itk.ac.id",
    ]
    assert [user["role"] for user in users] == ["ADMIN", "INSTRUCTOR", "STUDENT"]
    assert {user["status"] for user in users} == {"ACTIVE"}
    assert all(user["created_at"] for user in users)
    assert all(uuid.UUID(user["id"]) for user in users)
    assert set(users[0]) == {"id", "name", "email", "role", "status", "created_at"}


@pytest.mark.asyncio
async def test_admin_can_read_a_single_user(client, user_service):
    await create_user(user_service)
    instructor = await create_user(
        user_service, name="Dosen ITK", email="dosen@itk.ac.id", role=UserRole.INSTRUCTOR
    )

    response = await client.get(f"{ADMIN_USERS_URL}/{instructor.id}", headers=await login(client))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(instructor.id)
    assert body["email"] == "dosen@itk.ac.id"
    assert body["role"] == "INSTRUCTOR"


@pytest.mark.asyncio
async def test_admin_responses_never_expose_credentials(client, user_service):
    await create_user(user_service)

    response = await client.get(ADMIN_USERS_URL, headers=await login(client))

    assert "password" not in response.text.lower()
    assert "$2b$" not in response.text


@pytest.mark.parametrize("role", [UserRole.INSTRUCTOR, UserRole.STUDENT])
@pytest.mark.asyncio
async def test_non_admin_roles_are_denied(client, user_service, role):
    await create_user(user_service)
    await create_user(user_service, email="lain@itk.ac.id", role=role)
    headers = await login(client, username="lain@itk.ac.id")

    responses = [
        await client.get(ADMIN_USERS_URL, headers=headers),
        await client.get(f"{ADMIN_USERS_URL}/{uuid.uuid4()}", headers=headers),
    ]

    assert [response.status_code for response in responses] == [403, 403]
    assert {response.json()["error"]["code"] for response in responses} == {"AUTHORIZATION_DENIED"}


@pytest.mark.asyncio
async def test_unauthenticated_requests_are_denied(client, user_service):
    await create_user(user_service)

    responses = [
        await client.get(ADMIN_USERS_URL),
        await client.get(f"{ADMIN_USERS_URL}/{uuid.uuid4()}"),
    ]

    assert [response.status_code for response in responses] == [401, 401]
    assert {response.json()["error"]["code"] for response in responses} == {
        "AUTHENTICATION_FAILED"
    }


@pytest.mark.asyncio
async def test_unknown_user_is_reported_as_resource_not_found(client, user_service):
    await create_user(user_service)

    response = await client.get(f"{ADMIN_USERS_URL}/{uuid.uuid4()}", headers=await login(client))

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "RESOURCE_NOT_FOUND",
            "message": "Resource tidak ditemukan.",
            "details": [],
        }
    }


def test_admin_paths_are_part_of_the_api_spec():
    """Endpoint baru terdaftar pada OpenAPI di bawah prefix versi API."""
    paths = create_app().openapi()["paths"]

    assert ADMIN_USERS_URL in paths
    assert f"{ADMIN_USERS_URL}/{{user_id}}" in paths
