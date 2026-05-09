"""DB session lifecycle — engine, sessionmaker, dependency."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.logger import logger

# Modul-darajasidagi singletonlar
_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Async SQLAlchemy engine ni qaytaradi (lazy init)."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.LOG_LEVEL == "DEBUG",
            pool_pre_ping=True,
            # SQLite uchun maxsus
            connect_args={"check_same_thread": False}
            if settings.DATABASE_URL.startswith("sqlite")
            else {},
        )
        logger.info("🔌 DB engine yaratildi: {}", _mask_db_url(settings.DATABASE_URL))
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Async sessionmaker ni qaytaradi."""
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _sessionmaker


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager — handler/job ichida ishlatish uchun:

    ```python
    async with get_session() as session:
        ...
    ```

    Avtomatik commit/rollback va close qiladi.
    """
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_engine() -> None:
    """Bot to'xtaganda engine ni yopish (graceful shutdown)."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
        logger.info("🔌 DB engine yopildi")
        _engine = None
        _sessionmaker = None


def _mask_db_url(url: str) -> str:
    """Log uchun parolni yashirish."""
    if "@" not in url:
        return url
    scheme_part, _, rest = url.partition("://")
    creds, _, host = rest.rpartition("@")
    return f"{scheme_part}://***@{host}" if creds else url
