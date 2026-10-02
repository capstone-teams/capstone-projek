import shortuuid
import pytest
from sqlalchemy import select

from src.models.user import User, UserRole, UserStatus


def test_short_uuid_length():
    user_id = shortuuid.uuid()

    assert len(user_id) == 22


@pytest.mark.asyncio
async def test_create_user(db_session):
    user = User(
        name="Test User",
        email="test@example.com",
        password_hash="dummy-password-hash",
        role=UserRole.STUDENT,
        status=UserStatus.ACTIVE,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Pastikan ID dibuat otomatis (shortuuid, 22 karakter)
    assert user.id is not None
    assert len(user.id) == 22

    # Pastikan data sesuai
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    assert user.role == UserRole.STUDENT
    assert user.status == UserStatus.ACTIVE

    # Pastikan benar-benar bisa diambil dari database
    result = await db_session.execute(
        select(User).where(User.id == user.id)
    )
    saved_user = result.scalar_one()

    assert saved_user.id == user.id
    assert saved_user.name == "Test User"
    assert saved_user.email == "test@example.com"
    assert saved_user.role == UserRole.STUDENT


@pytest.mark.asyncio
async def test_email_must_be_unique(db_session):
    from sqlalchemy.exc import IntegrityError

    db_session.add(
        User(
            name="User 1",
            email="dup@example.com",
            role=UserRole.INSTRUCTOR,
            status=UserStatus.ACTIVE,
        )
    )
    await db_session.commit()

    db_session.add(
        User(
            name="User 2",
            email="dup@example.com",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()

@pytest.mark.asyncio
async def test_many_users_have_unique_shortuuid_ids(db_session):
    total = 10_000

    users = [
        User(
            name=f"User {i}",
            email=f"user{i}@example.com",
            password_hash="dummy-password-hash",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )
        for i in range(total)
    ]

    db_session.add_all(users)
    await db_session.commit()

    ids = [user.id for user in users]

    assert len(ids) == total
    assert all(len(user_id) == 22 for user_id in ids)
    assert len(set(ids)) == total
