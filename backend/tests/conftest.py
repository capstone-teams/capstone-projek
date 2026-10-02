"""Fixture pengujian backend.

Pengujian database memakai **SQLite in-memory** (aiosqlite) supaya seluruh suite
dapat dijalankan tanpa server PostgreSQL. Perilaku spesifik PostgreSQL (native
enum ``userrole``/``userstatus``, dsb.) diverifikasi pada pengujian integrasi
(BE-03.5) dengan database sungguhan.

Tipe kolom khusus PostgreSQL pada entity (``JSONB``) tetap dipakai apa adanya di
model dan migration — itu tipe yang benar untuk database produksi. Supaya suite
unit tetap dapat membangun skema pada SQLite, compiler untuk dialek SQLite
dipetakan ke ``JSON`` (lihat :func:`_compile_jsonb_for_sqlite`); pemetaan ini
hanya berlaku di dalam proses pengujian dan tidak menyentuh DDL PostgreSQL.
"""

from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from src.models.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(type_, compiler, **kw) -> str:
    """Render ``JSONB`` sebagai ``JSON`` pada SQLite (dialek pengujian)."""
    return "JSON"


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
