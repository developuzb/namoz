"""Tahajjud vaqti DM eslatma — `subscriptions.notify_nafl=True` userlar uchun.

Refresh job har kuni 00:05'da bugungi tahajjud start vaqtini hisoblab,
shu vaqt uchun bir martalik DateTrigger qo'shadi.
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


def _build_text(time_str: str, region_name: str) -> str:
    return (
        f"🌙 <b>Tahajjud vaqti boshlandi</b>\n"
        f"📍 <i>{escape_html(region_name)}</i>\n\n"
        f"⏰ <b>Vaqt:</b> <code>{escape_html(time_str)}</code>\n\n"
        f"🌌 Kechaning eng barakali soatlari...\n"
        f"<i>«Albatta, kechaning bir qismida o'qigan namoz qabul "
        f"qilinishi yaqindir.» — Toha 20:130</i>\n\n"
        f"🤲 2-8 rakat o'qish mumkin."
    )


async def fire_tahajjud_notification(
    bot: Bot, region_id: int, time_str: str
) -> None:
    """Bitta region uchun bugungi tahajjud vaqtida fire."""
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

        subs = await sub_repo.list_by_region(region_id, notify_nafl=True)
        if not subs:
            return

        text = _build_text(time_str, region.name)

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
                        await asyncio.sleep(e.retry_after + 1)
                        continue
                    errors += 1
                    msg = None
                    break
                except TelegramForbiddenError:
                    await user_repo.mark_blocked(user.tg_id)
                    await log_repo.log(
                        region_id=region_id, chat_id=user.tg_id,
                        post_type="tahajjud_notification", status="blocked",
                    )
                    blocked += 1
                    msg = None
                    break
                except TelegramBadRequest as e:
                    await log_repo.log(
                        region_id=region_id, chat_id=user.tg_id,
                        post_type="tahajjud_notification",
                        status="error", error=str(e),
                    )
                    errors += 1
                    msg = None
                    break

            if msg is None:
                continue

            await log_repo.log(
                region_id=region_id, chat_id=user.tg_id,
                post_type="tahajjud_notification",
                status="ok", message_id=msg.message_id,
            )
            sent += 1

            if delete_after > 0:
                asyncio.create_task(
                    _auto_delete(bot, user.tg_id, msg.message_id, delete_after)
                )

            await asyncio.sleep(0.05)

    logger.info(
        "🌙 Tahajjud {}: sent={} blocked={} errors={}",
        region.name, sent, blocked, errors,
    )


async def _auto_delete(bot: Bot, chat_id: int, message_id: int, delay: int) -> None:
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        pass
    except Exception as e:  # noqa: BLE001
        logger.debug("Auto-delete fail chat={}: {}", chat_id, e)


__all__ = ["fire_tahajjud_notification"]
