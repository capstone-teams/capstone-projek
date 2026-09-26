import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.config.settings import settings
from src.models.base import Base
from src.models.user import User

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the database URL from application settings.
config.set_main_option(
    "sqlalchemy.url",
    settings.async_database_url.replace("%", "%%"),
)

# Metadata used by Alembic autogenerate.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.async_database_url

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
