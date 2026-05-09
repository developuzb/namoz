"""Telegram qatlami — bot, handler, middleware, keyboard."""
from app.bot.factory import create_bot, create_dispatcher
from app.bot.handlers import register_routers

__all__ = ["create_bot", "create_dispatcher", "register_routers"]
