"""Fixture pengujian backend.

Pengujian database memakai **SQLite in-memory** (aiosqlite) supaya seluruh suite
dapat dijalankan tanpa server PostgreSQL. Perilaku spesifik PostgreSQL (native
enum ``userrole``/``userstatus``, dsb.) diverifikasi pada pengujian integrasi
(BE-03.5) dengan database sungguhan.
"""

from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Session database dengan skema yang dibangun dari ``Base.metadata``.

    Setiap test mendapat engine dan skema sendiri, sehingga urutan test tidak
    mempengaruhi hasil. ``expire_on_commit`` dibiarkan pada nilai default agar
    kombinasi commit + refresh pada repository benar-benar teruji.
    """
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine)
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()
