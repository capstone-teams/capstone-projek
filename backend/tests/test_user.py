"""Test entity ORM ``User`` (BE-02).

Berbeda dengan ``tests/test_user_domain.py`` (aturan domain) dan
``tests/test_user_service.py`` (operasi aplikasi), test ini bekerja langsung
pada entity tabel: pembentukan identifier ShortUUID oleh database foundation,
serta unique constraint ``users.email`` dan ``users.username``.

Field mengikuti atribut user Moodle (``username``, ``firstname``, ``lastname``,
``email``, ``password``); ``password`` berisi hash, bukan password mentah.
"""

import re

import pytest
import shortuuid
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.models.base import ID_LENGTH
from src.models.user import User, UserRole, UserStatus
from src.services.user.validation import SHORTUUID_PATTERN


def build_user(**overrides) -> User:
    """Entity user valid dengan nilai default, dipakai sebagai basis tiap test."""
    payload = {
        "username": "test.user",
        "firstname": "Test",
        "lastname": "User",
        "email": "test@example.com",
        "password": "dummy-password-hash",
        "role": UserRole.STUDENT,
        "status": UserStatus.ACTIVE,
    }
    payload.update(overrides)
    return User(**payload)


def test_short_uuid_length():
    user_id = shortuuid.uuid()

    assert len(user_id) == ID_LENGTH


@pytest.mark.asyncio
async def test_create_user(db_session):
    user = build_user()

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # ID dibuat otomatis oleh database foundation (ShortUUID, 22 karakter).
    assert user.id is not None
    assert len(user.id) == ID_LENGTH
    assert re.fullmatch(SHORTUUID_PATTERN, user.id)

    assert user.username == "test.user"
    assert user.firstname == "Test"
    assert user.lastname == "User"
    assert user.email == "test@example.com"
    assert user.role == UserRole.STUDENT
    assert user.status == UserStatus.ACTIVE

    # Benar-benar tersimpan dan bisa diambil kembali dari database.
    result = await db_session.execute(select(User).where(User.id == user.id))
    saved_user = result.scalar_one()

    assert saved_user.id == user.id
    assert saved_user.username == "test.user"
    assert saved_user.firstname == "Test"
    assert saved_user.lastname == "User"
    assert saved_user.email == "test@example.com"
    assert saved_user.role == UserRole.STUDENT


@pytest.mark.asyncio
async def test_email_must_be_unique(db_session):
    db_session.add(build_user(username="user.one", email="dup@example.com"))
    await db_session.commit()

    db_session.add(build_user(username="user.two", email="dup@example.com"))

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_username_must_be_unique(db_session):
    """``username`` adalah atribut Moodle dan kolom UNIQUE."""
    db_session.add(build_user(username="dosen.itk", email="satu@example.com"))
    await db_session.commit()

    db_session.add(build_user(username="dosen.itk", email="dua@example.com"))

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_person_name_columns_are_required(db_session):
    """``firstname``/``lastname`` NOT NULL: entity tanpa keduanya ditolak database."""
    db_session.add(build_user(firstname=None))

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_identifier_length_is_enforced_by_the_database(db_session):
    """Constraint ``length(id) = 22`` menolak identifier yang salah panjang."""
    db_session.add(build_user(id="terlalu-pendek"))

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_many_users_have_unique_shortuuid_ids(db_session):
    total = 10_000

    users = [
        build_user(username=f"user{i}", email=f"user{i}@example.com")
        for i in range(total)
    ]

    db_session.add_all(users)
    # Identifier dibentuk oleh default Python-side saat flush, sehingga nilainya
    # sudah terbaca sebelum commit tanpa memicu load ulang (session test memakai
    # ``expire_on_commit`` default).
    await db_session.flush()

    ids = [user.id for user in users]
    await db_session.commit()

    assert len(ids) == total
    assert all(len(user_id) == ID_LENGTH for user_id in ids)
    assert all(re.fullmatch(SHORTUUID_PATTERN, user_id) for user_id in ids)
    assert len(set(ids)) == total
