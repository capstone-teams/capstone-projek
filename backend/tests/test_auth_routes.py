"""Test endpoint authentication (BE-03.3) pada SQLite in-memory.

Endpoint diuji melalui ASGI app (httpx ASGITransport) dengan dependency
override ke session test, sehingga kontrak HTTP, pemetaan error 401, dan
response DTO benar-benar terverifikasi.
"""

from datetime import timedelta

import httpx
import pytest
import pytest_asyncio

from src.main import create_app
from src.services.auth import create_access_token, hash_password
from src.services.dependencies import get_db_session
from src.services.user import UserRole, UserService

PASSWORD = "SecretPassword123"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"


@pytest_asyncio.fixture
async def client(db_session) -> httpx.AsyncClient:
    """Client HTTP ke aplikasi dengan session database test."""
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
        "name": "Dosen ITK",
        "email": "dosen@itk.ac.id",
        "role": UserRole.INSTRUCTOR,
        "password_hash": hash_password(PASSWORD),
    }
    payload.update(overrides)
    return await user_service.create_user(**payload)


async def login(client: httpx.AsyncClient, **overrides) -> httpx.Response:
    payload = {"username": "dosen@itk.ac.id", "password": PASSWORD}
    payload.update(overrides)
    return await client.post(LOGIN_URL, json=payload)


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_returns_access_token_and_role(client, user_service):
    created = await create_user(user_service)

    response = await login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"] == {"id": str(created.id), "role": "INSTRUCTOR"}


@pytest.mark.asyncio
async def test_login_response_never_contains_credentials(client, user_service):
    await create_user(user_service)

    response = await login(client)

    assert "password" not in response.text.lower()
    assert "$2b$" not in response.text


@pytest.mark.asyncio
async def test_login_with_wrong_password_is_rejected(client, user_service):
    await create_user(user_service)

    response = await login(client, password="PasswordSalah123")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_login_failures_are_indistinguishable(client, user_service):
    """Unknown user, wrong password, inactive, dan tanpa credential -> response sama."""
    await create_user(user_service, email="nonaktif@itk.ac.id")
    inactive = await user_service.get_user_by_email("nonaktif@itk.ac.id")
    await user_service.deactivate_user(inactive.id)
    await create_user(user_service, email="tanpa-hash@itk.ac.id", password_hash=None)

    responses = [
        await login(client, username="tidak-ada@itk.ac.id"),
        await login(client, password="PasswordSalah123"),
        await login(client, username="nonaktif@itk.ac.id"),
        await login(client, username="tanpa-hash@itk.ac.id"),
    ]

    assert [response.status_code for response in responses] == [401, 401, 401, 401]
    assert len({response.text for response in responses}) == 1


@pytest.mark.asyncio
async def test_login_with_incomplete_payload_is_a_validation_error(client, user_service):
    await create_user(user_service)

    response = await client.post(LOGIN_URL, json={"username": "dosen@itk.ac.id", "password": ""})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_ignores_client_supplied_role(client, user_service):
    """Client tidak dapat menentukan role: role berasal dari record User."""
    created = await create_user(user_service, role=UserRole.STUDENT)

    response = await client.post(
        LOGIN_URL,
        json={"username": "dosen@itk.ac.id", "password": PASSWORD, "role": "ADMIN"},
    )

    assert response.status_code == 200
    assert response.json()["user"] == {"id": str(created.id), "role": "STUDENT"}


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_me_returns_the_authenticated_user(client, user_service):
    created = await create_user(user_service)
    token = (await login(client)).json()["access_token"]

    response = await client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "id": str(created.id),
        "name": "Dosen ITK",
        "email": "dosen@itk.ac.id",
        "role": "INSTRUCTOR",
    }
    assert "password" not in response.text.lower()


@pytest.mark.asyncio
async def test_me_without_authentication_is_rejected(client):
    response = await client.get(ME_URL)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "header",
    ["Bearer bukan-token", "Token abc", "Bearer", "Basic ZG9zZW46cGFzcw=="],
)
async def test_me_with_invalid_authorization_header_is_rejected(client, header):
    response = await client.get(ME_URL, headers={"Authorization": header})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_expired_token_is_rejected(client, user_service):
    created = await create_user(user_service)
    expired = create_access_token(created.id, expires_delta=timedelta(seconds=-1))

    response = await client.get(ME_URL, headers={"Authorization": f"Bearer {expired}"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_is_rejected_after_deactivation(client, user_service):
    created = await create_user(user_service)
    token = (await login(client)).json()["access_token"]

    await user_service.deactivate_user(created.id)

    response = await client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_public_endpoint_stays_accessible_without_authentication(client):
    response = await client.get("/health")

    assert response.status_code == 200
