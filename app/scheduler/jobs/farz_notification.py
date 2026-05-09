"""Farz vaqti DM eslatma — `subscriptions.notify_farz=True` userlar uchun.

Eski koddagi bug'lar tuzatildi:
- Eslatma KANALGA emas, DM ga yuboriladi
- `asyncio.get_event_loop().call_later` o'rniga `asyncio.create_task` (Py 3.12+ safe)
"""
from __future__ import annotations

import asyncio

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)

from app.core.config import get_settings
from app.core.logger import logger
from app.db.repositories.post_log_repo import PostLogRepository
from app.db.repositories.region_repo import RegionRepository
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.db.repositories.user_repo import UserRepository
from app.db.session import get_session
from app.utils.text_utils import escape_html


def _build_text(prayer: str, time_str: str, region_name: str) -> str:
    return (
        f"🕋 <b>{escape_html(prayer)} namozi vaqti kirdi</b>\n"
        f"📍 <i>{escape_html(region_name)}</i>\n\n"
        f"⏰ <b>Vaqt:</b> <code>{escape_html(time_str)}</code>\n\n"
        f"🤲 Bir necha daqiqa…\n"
        f"Dunyo ishlari kutadi, namoz esa kutmaydi.\n\n"
        f"🌿 <i>Vaqtida o'qilgan namoz qalbga xotirjamlik olib keladi.</i>"
    )


async def fire_farz_notification(
    bot: Bot, region_id: int, prayer: str, time_str: str
) -> None:
    """Bitta region/farz uchun bir martalik fire (scheduler DateTrigger)."""
    settings = get_settings()
    delete_after = settings.NOTIFICATION_DELETE_AFTER

    async with get_session() as session:
        rr = RegionRepository(session)
        sub_repo = SubscriptionRepository(session)
        log_repo = PostLogRepository(session)
        user_repo = UserRepository(session)

        region = await rr.get(region_id)
        if region is None or not region.is_active:
            return

        subs = await sub_repo.list_by_region(region_id, notify_farz=True)
        if not subs:
            logger.debug("Farz {}/{}: obunachi yo'q", region.name, prayer)
            return

        text = _build_text(prayer, time_str, region.name)

        sent = 0
        blocked = 0
        errors = 0

        for sub in subs:
            user = sub.user
            if user.is_blocked:
                continue

            msg = None
            for attempt in range(2):
                try:
                    msg = await bot.send_message(user.tg_id, text)
                    break
                except TelegramRetryAfter as e:
                    if attempt == 0:
                        logger.warning("Rate limit tg={}, kutamiz {}s", user.tg_id, e.retry_after)
                        await asyncio.sleep(e.retry_after + 1)
                        continue
                    errors += 1
                    msg = None
                    break
                except TelegramForbiddenError:
                    await user_repo.mark_blocked(user.tg_id)
                    await log_repo.log(
                        region_id=region_id, chat_id=user.tg_id,
                        post_type="farz_notification", status="blocked",
                    )
                    blocked += 1
                    msg = None
                    break
                except TelegramBadRequest as e:
                    await log_repo.log(
                        region_id=region_id, chat_id=user.tg_id,
                        post_type="farz_notification", status="error", error=str(e),
                    )
                    errors += 1
                    msg = None
                    break
            if msg is None:
                continue

            await log_repo.log(
                region_id=region_id, chat_id=user.tg_id,
                post_type="farz_notification",
                status="ok", message_id=msg.message_id,
            )
            sent += 1

            if delete_after > 0:
                # Auto-delete (eski kodda call_later edi — endi create_task)
                asyncio.create_task(
                    _auto_delete(bot, user.tg_id, msg.message_id, delete_after)
                )

            await asyncio.sleep(0.05)  # rate limit

    logger.info(
        "🔔 Farz {}/{}: sent={} blocked={} errors={}",
        region.name, prayer, sent, blocked, errors,
    )


async def _auto_delete(bot: Bot, chat_id: int, message_id: int, delay: int) -> None:
    """Belgilangan vaqtdan keyin xabarni o'chiradi."""
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        pass  # xabar allaqachon o'chgan / user bloklagan
    except Exception as e:
        logger.debug("Auto-delete fail chat={}: {}", chat_id, e)


__all__ = ["fire_farz_notification"]
