"""Alembic env — async DB bilan ishlash uchun."""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ⚠️ MUHIM: barcha modellarni import qilish kerak,
# aks holda Alembic ularni "ko'rmaydi"
from app.core.config import get_settings
from app.db.base import Base
from app.db.models import (  # noqa: F401  -- import for side-effect
    Channel,
    MasjidTime,
    PostLog,
    Region,
    StatEvent,
    SubscribedChat,
    Subscription,
    User,
)

# Alembic Config obyekti
config = context.config

# .env dan DB URL ni o'rnatish
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Avto-migrasiya uchun metadata
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Offline rejim — DB ga ulanmasdan SQL faylini chiqaradi."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # SQLite uchun MUHIM (ALTER TABLE cheklovlari)
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # SQLite
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Online rejim — async engine bilan."""
    # Postgres (Heroku) uchun SSL connect_args — session.py bilan bir xil.
    from app.db.session import _build_connect_args

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=_build_connect_args(settings.DATABASE_URL),
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
