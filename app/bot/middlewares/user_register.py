"""User register middleware — Telegram user ni DB User ga aylantiradi."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update
from aiogram.types import User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logger import logger
from app.db.repositories.user_repo import UserRepository


class UserRegisterMiddleware(BaseMiddleware):
    """
    `event.from_user` ni DB User ga aylantirib `data["user"]` ga inject qiladi.
    Shuningdek `data["is_admin"]` ni hisoblaydi (env ADMIN_IDS yoki users.is_admin).

    Channel post va botlar uchun `user=None`, `is_admin=False` qaytadi.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = self._extract_user(event)
        logger.debug(
            "[UserRegister] event_type={} tg_user={}",
            type(event).__name__,
            tg_user.id if tg_user else None,
        )

        if tg_user is None or tg_user.is_bot:
            data["user"] = None
            data["is_admin"] = False
            return await handler(event, data)

        session: AsyncSession | None = data.get("session")
        if session is None:
            logger.error("[UserRegister] data['session'] yo'q!")
            data["user"] = None
            data["is_admin"] = False
            return await handler(event, data)

        user_repo = UserRepository(session)

        user, created = await user_repo.get_or_create(
            tg_id=tg_user.id,
            username=tg_user.username,
            full_name=tg_user.full_name,
            language=tg_user.language_code or "uz",
        )

        if created:
            logger.info(
                "🆕 Yangi user: tg_id={} @{} ({})",
                tg_user.id, tg_user.username, tg_user.full_name,
            )

        admin_ids = set(get_settings().admin_ids_list)
        is_admin = user.is_admin or (tg_user.id in admin_ids)

        data["user"] = user
        data["is_admin"] = is_admin

        return await handler(event, data)

    @staticmethod
    def _extract_user(event: TelegramObject) -> TgUser | None:
        # `dp.update.outer_middleware` da event = Update (xom ko'rinishda)
        if isinstance(event, Update):
            if event.message:
                return event.message.from_user
            if event.edited_message:
                return event.edited_message.from_user
            if event.callback_query:
                return event.callback_query.from_user
            if event.my_chat_member:
                return event.my_chat_member.from_user
            return None
        # Inner middleware'da event = Message/CallbackQuery
        if isinstance(event, (Message, CallbackQuery)):
            return event.from_user
        return None
