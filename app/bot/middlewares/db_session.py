"""DB session middleware — har update uchun yangi `AsyncSession` ochadi."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.core.logger import logger
from app.db.session import get_sessionmaker


class DBSessionMiddleware(BaseMiddleware):
    """
    Handler chaqirilishidan oldin `data["session"]` ga yangi `AsyncSession`
    qo'yadi, handler tugagach commit/rollback qilib yopadi.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        logger.debug("[DBSession] event_type={}", type(event).__name__)
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception as e:
                logger.exception("[DBSession] handler error: {}", e)
                await session.rollback()
                raise
