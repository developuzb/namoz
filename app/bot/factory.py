"""Bot va Dispatcher ni yaratish."""
from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.config import get_settings
from app.core.logger import logger


def create_bot() -> Bot:
    """Token + default HTML parse mode bilan Bot instance."""
    settings = get_settings()
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    logger.debug("Bot instance yaratildi")
    return bot


def create_dispatcher() -> Dispatcher:
    """In-memory FSM storage bilan Dispatcher."""
    dp = Dispatcher(storage=MemoryStorage())
    logger.debug("Dispatcher yaratildi (FSM: MemoryStorage)")
    return dp


__all__ = ["create_bot", "create_dispatcher"]
