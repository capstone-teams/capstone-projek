"""Test integrasi authentication pada PostgreSQL sungguhan (BE-03.3).

Test ini dijalankan terhadap database yang dikonfigurasi pada
``Settings.async_database_url`` (lihat ``backend/.env``) dan **dilewati** bila
database tidak dapat dijangkau, sehingga ``pytest`` tetap hijau di lingkungan
tanpa PostgreSQL.

Tujuannya memverifikasi perilaku yang tidak dapat direpresentasikan SQLite:
native enum ``userrole``/``userstatus``, unique constraint ``users_email_key``,
dan default ``now()`` pada kolom timestamp.

Menjalankan:

    docker run --name capstone-postgres -e POSTGRES_USER=postgres \\
        -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=lms_moodle_db \\
        -p 5432:5432 -d postgres:16
    cd backend && uv run alembic upgrade head && uv run pytest tests/test_auth_postgres.py
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config.settings import settings
from src.main import create_app
from src.models.base import Base
from src.models.user import User as UserEntity
from src.services.auth import hash_password
from src.services.dependencies import get_db_session
from src.services.user import DuplicateEmailError, UserRole, UserService, UserStatus

PASSWORD = "SecretPassword123"
EMAIL_PREFIX = "auth-it-"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"

CONNECT_TIMEOUT_SECONDS = 5


@pytest_asyncio.fixture
async def postgres_session() -> AsyncIterator[AsyncSession]:
    """Session PostgreSQL sungguhan; test dilewati bila database tidak tersedia."""
    engine = create_async_engine(
        settings.async_database_url,
        connect_args={"timeout": CONNECT_TIMEOUT_SECONDS},
    )
    try:
        try:
            async with engine.begin() as connection:
                await asyncio.wait_for(
                    connection.run_sync(Base.metadata.create_all),
                    timeout=CONNECT_TIMEOUT_SECONDS,
                )
        except (OSError, SQLAlchemyError, asyncio.TimeoutError) as exc:
            await engine.dispose()
            pytest.skip(f"PostgreSQL tidak tersedia pada {settings.DB_HOST}:{settings.DB_PORT} ({exc})")

        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            yield session

        async with async_sessionmaker(engine, expire_on_commit=False)() as cleanup:
            await cleanup.execute(delete(UserEntity).where(UserEntity.email.like(f"{EMAIL_PREFIX}%")))
            await cleanup.commit()
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def service(postgres_session) -> UserService:
    return UserService.from_session(postgres_session)


@pytest_asyncio.fixture
async def client(postgres_session) -> AsyncIterator[httpx.AsyncClient]:
    application = create_app()

    async def override_get_db_session():
        yield postgres_session

    application.dependency_overrides[get_db_session] = override_get_db_session
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client
    application.dependency_overrides.clear()


async def create_user(service: UserService, **overrides):
    payload = {
        "name": "Dosen Integration Test",
        "email": f"{EMAIL_PREFIX}{uuid.uuid4().hex[:8]}@itk.ac.id",
        "role": UserRole.INSTRUCTOR,
        "password_hash": hash_password(PASSWORD),
    }
    payload.update(overrides)
    return await service.create_user(**payload)


@pytest.mark.asyncio
async def test_user_round_trip_uses_native_postgres_enum_and_constraints(service):
    created = await create_user(service)

    stored = await service.get_user(created.id)

    assert stored.role is UserRole.INSTRUCTOR
    assert stored.status is UserStatus.ACTIVE
    assert stored.created_at is not None
    assert stored.updated_at is not None
    assert isinstance(stored.id, uuid.UUID)


@pytest.mark.asyncio
async def test_duplicate_email_is_rejected_by_the_database_constraint(service):
    created = await create_user(service)

    with pytest.raises(DuplicateEmailError):
        await create_user(service, email=created.email)

    assert await service.is_email_registered(created.email) is True


@pytest.mark.asyncio
async def test_login_and_me_flow_against_real_database(client, service):
    created = await create_user(service, role=UserRole.STUDENT)

    login_response = await client.post(
        LOGIN_URL, json={"username": created.email.upper(), "password": PASSWORD}
    )

    assert login_response.status_code == 200
    body = login_response.json()
    assert body["token_type"] == "bearer"
    assert body["user"] == {"id": str(created.id), "role": "STUDENT"}
    assert "password" not in login_response.text.lower()

    me_response = await client.get(
        ME_URL, headers={"Authorization": f"Bearer {body['access_token']}"}
    )

    assert me_response.status_code == 200
    assert me_response.json() == {
        "id": str(created.id),
        "name": created.name,
        "email": created.email,
        "role": "STUDENT",
    }


@pytest.mark.asyncio
async def test_login_failure_and_inactive_user_are_rejected_in_real_database(client, service):
    created = await create_user(service)

    wrong_password = await client.post(
        LOGIN_URL, json={"username": created.email, "password": "PasswordSalah123"}
    )
    unknown_user = await client.post(
        LOGIN_URL, json={"username": f"{EMAIL_PREFIX}tidak-ada@itk.ac.id", "password": PASSWORD}
    )

    assert wrong_password.status_code == 401
    assert wrong_password.json()["error"]["code"] == "AUTHENTICATION_FAILED"
    assert wrong_password.text == unknown_user.text

    await service.deactivate_user(created.id)
    inactive = await client.post(
        LOGIN_URL, json={"username": created.email, "password": PASSWORD}
    )

    assert inactive.status_code == 401
    assert inactive.text == wrong_password.text


@pytest.mark.asyncio
async def test_protected_endpoint_requires_a_valid_token_in_real_database(client, service):
    created = await create_user(service)
    token = (
        await client.post(LOGIN_URL, json={"username": created.email, "password": PASSWORD})
    ).json()["access_token"]

    without_token = await client.get(ME_URL)
    with_token = await client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})

    assert without_token.status_code == 401
    assert with_token.status_code == 200

    # Role mengikuti record User, bukan klaim token.
    await service.update_user(created.id, role=UserRole.ADMIN)
    after_role_change = await client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})

    assert after_role_change.json()["role"] == "ADMIN"
