"""Barcha handlerlarni Dispatcher ga ulash."""
from aiogram import Dispatcher

from app.bot.handlers.admin import router as admin_router
from app.bot.handlers.group_chat import router as group_chat_router
from app.bot.handlers.inline import router as inline_router
from app.bot.handlers.user import router as user_router


def register_routers(dp: Dispatcher) -> None:
    """Dispatcher ga router larni qo'shish.

    Tartib MUHIM:
    - admin router avval (filter bilan)
    - group_chat router — F.chat.type filtri bilan, faqat guruhlardagi xabarlar
    - user router — DM uchun (eng oxirida fallback)
    - inline router — `inline_query` event'lari uchun (chat'siz)
    """
    dp.include_router(admin_router)
    dp.include_router(group_chat_router)
    dp.include_router(user_router)
    dp.include_router(inline_router)


__all__ = ["register_routers"]
