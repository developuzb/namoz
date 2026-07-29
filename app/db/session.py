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


def _build_connect_args(db_url: str) -> dict:
    """Dialektga qarab connect_args tuzadi.

    - SQLite: `check_same_thread=False` (async uchun).
    - Postgres (Heroku): SSL majburiy. Heroku sertifikati self-signed
      bo'lishi mumkin, shuning uchun tekshirmasdan SSL ishlatiladi.
    """
    if db_url.startswith("sqlite"):
        return {"check_same_thread": False}
    if db_url.startswith("postgresql"):
        import ssl

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return {"ssl": ctx}
    return {}


def get_engine() -> AsyncEngine:
    """Async SQLAlchemy engine ni qaytaradi (lazy init)."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.LOG_LEVEL == "DEBUG",
            pool_pre_ping=True,
            connect_args=_build_connect_args(settings.DATABASE_URL),
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
