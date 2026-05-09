"""Kunlik post job — har kuni belgilangan vaqtda.

Ishlash tartibi:
1. Postga muhtoj barcha regionlarni topish (channel'li yoki daily_post=True userli)
2. Har region uchun bitta `PostBundle` yasash (rasm + caption)
3. Bundle ni:
   a) shu region'ning aktiv kanallariga jo'natish
   b) shu region'ga obuna bo'lgan + daily_post=True userlarga DM ga jo'natish
4. Har bir yuborish uchun `post_logs` ga yozuv qo'shish
"""
from __future__ import annotations

import asyncio
from datetime import date

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.types import FSInputFile
from sqlalchemy import select

from app.core.exceptions import ProviderError
from app.core.logger import logger
from app.db.models.subscription import Subscription
from app.db.repositories.channel_repo import ChannelRepository
from app.db.repositories.post_log_repo import PostLogRepository
from app.db.repositories.region_repo import RegionRepository
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.db.repositories.user_repo import UserRepository
from app.db.session import get_session
from app.services.registry import get_post_service

#: Telegram'ga zaxira: yuborish orasida kichik pauza
_SEND_DELAY = 0.1


async def run_daily_post(bot: Bot) -> None:
    """Asosiy entry point — scheduler chaqiradi."""
    today = date.today()
    post_service = get_post_service()

    async with get_session() as session:
        ch_repo = ChannelRepository(session)
        sub_repo = SubscriptionRepository(session)
        log_repo = PostLogRepository(session)
        user_repo = UserRepository(session)
        rr = RegionRepository(session)

        channels = await ch_repo.list_active_with_region()

        # daily_post=True bo'lgan obunalardagi region_id'larni yig'amiz
        result = await session.execute(
            select(Subscription.region_id)
            .distinct()
            .where(Subscription.daily_post.is_(True))
        )
        sub_region_ids = {r[0] for r in result}

        region_ids: set[int] = {ch.region_id for ch in channels} | sub_region_ids

        logger.info(
            "🗓 Kunlik post boshlandi: {} region (channels={}, sub_regions={})",
            len(region_ids), len(channels), len(sub_region_ids),
        )

        sent_ok = 0
        sent_fail = 0

        for region_id in region_ids:
            region = await rr.get(region_id)
            if region is None or not region.is_active:
                continue

            # 1. Bundle (rasm + caption) yasash — provider chain orqali
            try:
                bundle = await post_service.build_for_region(
                    session=session, region=region, target_date=today,
                )
            except ProviderError as e:
                logger.error("Daily post: provider failed for {}: {}", region.name, e)
                # Har bir maqsad uchun xato yozish
                for ch in channels:
                    if ch.region_id == region_id:
                        await log_repo.log(
                            region_id=region_id, chat_id=ch.chat_id,
                            post_type="daily", status="error", error=str(e),
                        )
                continue

            # 2. Kanallarga
            for ch in channels:
                if ch.region_id != region_id:
                    continue

                caption = bundle.caption
                if ch.link:
                    caption = f"{caption}\n\n🔗 {ch.link}"
                if ch.custom_caption_template:
                    caption = f"{caption}\n\n{ch.custom_caption_template}"

                ok = await _send_photo_safe(
                    bot=bot,
                    chat_id=ch.chat_id,
                    image_path=str(bundle.image_path),
                    caption=caption,
                    log_repo=log_repo,
                    user_repo=None,  # kanal uchun mark_blocked yo'q
                    region_id=region_id,
                    post_type="daily",
                )
                if ok:
                    sent_ok += 1
                else:
                    sent_fail += 1
                await asyncio.sleep(_SEND_DELAY)

            # 3. DM obunachilariga
            subs = await sub_repo.list_by_region(region_id, daily_post=True)
            for sub in subs:
                user = sub.user
                if user.is_blocked:
                    continue

                ok = await _send_photo_safe(
                    bot=bot,
                    chat_id=user.tg_id,
                    image_path=str(bundle.image_path),
                    caption=bundle.caption,
                    log_repo=log_repo,
                    user_repo=user_repo,
                    region_id=region_id,
                    post_type="daily",
                )
                if ok:
                    sent_ok += 1
                else:
                    sent_fail += 1
                await asyncio.sleep(_SEND_DELAY)

        logger.info("✅ Kunlik post tugadi: ok={} fail={}", sent_ok, sent_fail)


async def _send_photo_safe(
    *,
    bot: Bot,
    chat_id: int,
    image_path: str,
    caption: str,
    log_repo: PostLogRepository,
    user_repo: UserRepository | None,
    region_id: int,
    post_type: str,
) -> bool:
    """Photo yuboradi va xato bilan ishlaydi. Returns True if delivered.

    `TelegramRetryAfter` bo'lsa Telegram talab qilgan vaqt kutilib, bir marta
    qayta urinib ko'riladi.
    """
    for attempt in range(2):
        try:
            msg = await bot.send_photo(
                chat_id=chat_id,
                photo=FSInputFile(image_path),
                caption=caption,
            )
        except TelegramRetryAfter as e:
            if attempt == 0:
                logger.warning("Rate limit chat_id={}, kutamiz {}s", chat_id, e.retry_after)
                import asyncio as _asyncio
                await _asyncio.sleep(e.retry_after + 1)
                continue
            await log_repo.log(
                region_id=region_id, chat_id=chat_id,
                post_type=post_type, status="error",
                error=f"retry_after exhausted: {e}",
            )
            return False
        except TelegramForbiddenError:
            if user_repo is not None:
                await user_repo.mark_blocked(chat_id)
            await log_repo.log(
                region_id=region_id, chat_id=chat_id,
                post_type=post_type, status="blocked",
            )
            logger.warning("Bloklangan: chat_id={}", chat_id)
            return False
        except TelegramBadRequest as e:
            await log_repo.log(
                region_id=region_id, chat_id=chat_id,
                post_type=post_type, status="error", error=str(e),
            )
            logger.error("Send fail chat_id={}: {}", chat_id, e)
            return False
        except Exception as e:
            await log_repo.log(
                region_id=region_id, chat_id=chat_id,
                post_type=post_type, status="error", error=str(e),
            )
            logger.exception("Send unexpected error chat_id={}: {}", chat_id, e)
            return False

        await log_repo.log(
            region_id=region_id, chat_id=chat_id,
            post_type=post_type, status="ok", message_id=msg.message_id,
        )
        return True
    return False


__all__ = ["run_daily_post"]
