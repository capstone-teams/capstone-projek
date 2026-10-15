"""Infrastruktur database: async engine dan session factory.

Modul ini hanya menyiapkan resource koneksi (tanpa FastAPI dan tanpa logika
domain) supaya layer lain tidak perlu membangun engine sendiri. Provider
dependency untuk HTTP berada di ``src/services/dependencies.py``.

Engine dibuat *lazy* saat pertama dipakai dan ditutup melalui
:func:`dispose_engine` pada saat shutdown aplikasi (lihat lifespan di
``src/main.py``).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config.settings import settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Engine async tunggal untuk proses ini."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.async_database_url,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Session factory di atas engine aplikasi.

    ``expire_on_commit=False`` dipakai agar objek hasil operasi tetap dapat
    dibaca setelah commit; repository tetap melakukan ``refresh`` eksplisit
    untuk metadata yang dibentuk database.
    """
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def dispose_engine() -> None:
    """Tutup pool koneksi dan lupakan engine (dipakai saat shutdown)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
