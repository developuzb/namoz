"""Barcha handlerlarni Dispatcher ga ulash."""
from aiogram import Dispatcher

from app.bot.handlers.admin import router as admin_router
from app.bot.handlers.user import router as user_router


def register_routers(dp: Dispatcher) -> None:
    """Dispatcher ga router larni qo'shish.

    Tartib MUHIM: admin router avval (filter bilan), keyin user router (fallback).
    """
    dp.include_router(admin_router)
    dp.include_router(user_router)


__all__ = ["register_routers"]
