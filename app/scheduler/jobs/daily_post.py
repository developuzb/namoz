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
from pathlib import Path

from aiogram import Bot
from sqlalchemy import select

from app.core.exceptions import ProviderError
from app.core.logger import logger
from app.db.models.subscription import Subscription
from app.db.repositories.channel_repo import ChannelRepository
from app.db.repositories.post_log_repo import PostLogRepository
from app.db.repositories.region_repo import RegionRepository
from app.db.repositories.subscribed_chat_repo import SubscribedChatRepository
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.db.repositories.user_repo import UserRepository
from app.db.session import get_session
from app.services.registry import get_post_service
from app.services.telegram_send import (
    notify_admins,
    send_document_safe,
    send_photo_safe,
)
from app.utils.text_utils import escape_html

#: Telegram'ga zaxira: yuborish orasida kichik pauza
_SEND_DELAY = 0.1


async def run_daily_post(bot: Bot) -> None:
    """Asosiy entry point — scheduler chaqiradi."""
    today = date.today()
    post_service = get_post_service()

    async with get_session() as session:
        ch_repo = ChannelRepository(session)
        sub_repo = SubscriptionRepository(session)
        sc_repo = SubscribedChatRepository(session)
        log_repo = PostLogRepository(session)
        user_repo = UserRepository(session)
        rr = RegionRepository(session)

        channels = await ch_repo.list_active_with_region()
        group_chats = await sc_repo.list_active_with_region()
        # Faqat daily_post=True bo'lgan guruhlar
        group_chats = [g for g in group_chats if g.daily_post]

        # daily_post=True bo'lgan obunalardagi region_id'larni yig'amiz
        result = await session.execute(
            select(Subscription.region_id)
            .distinct()
            .where(Subscription.daily_post.is_(True))
        )
        sub_region_ids = {r[0] for r in result}
        group_region_ids = {g.region_id for g in group_chats}

        region_ids: set[int] = (
            {ch.region_id for ch in channels} | sub_region_ids | group_region_ids
        )

        logger.info(
            "🗓 Kunlik post boshlandi: {} region (channels={}, groups={}, "
            "sub_regions={})",
            len(region_ids), len(channels), len(group_chats), len(sub_region_ids),
        )

        sent_ok = 0
        sent_fail = 0
        #: Manba (provider) ishlamay post yasay olmagan hududlar
        failed_regions: list[str] = []
        last_provider_error: str = ""

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
                failed_regions.append(region.name)
                last_provider_error = str(e)
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

                ok = await send_photo_safe(
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
                    # Maksimal sifat — siqilmagan HD nusxa (fayl sifatida)
                    await send_document_safe(
                        bot=bot,
                        chat_id=ch.chat_id,
                        file_path=str(bundle.image_path),
                        filename=f"HD_{Path(bundle.image_path).name}",
                    )
                else:
                    sent_fail += 1
                await asyncio.sleep(_SEND_DELAY)

            # 3. Guruh chatlariga
            for gc in group_chats:
                if gc.region_id != region_id:
                    continue
                ok = await send_photo_safe(
                    bot=bot,
                    chat_id=gc.chat_id,
                    image_path=str(bundle.image_path),
                    caption=bundle.caption,
                    log_repo=log_repo,
                    user_repo=None,  # group — mark_blocked yo'q
                    region_id=region_id,
                    post_type="daily_group",
                )
                if ok:
                    sent_ok += 1
                    # Maksimal sifat — siqilmagan HD nusxa (fayl sifatida)
                    await send_document_safe(
                        bot=bot,
                        chat_id=gc.chat_id,
                        file_path=str(bundle.image_path),
                        filename=f"HD_{Path(bundle.image_path).name}",
                    )
                else:
                    sent_fail += 1
                await asyncio.sleep(_SEND_DELAY)

            # 4. DM obunachilariga
            subs = await sub_repo.list_by_region(region_id, daily_post=True)
            for sub in subs:
                user = sub.user
                if user.is_blocked:
                    continue

                ok = await send_photo_safe(
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

    # Manba ishlamay qolgan hududlar bo'lsa — adminlarga ogohlantirish
    if failed_regions:
        await _notify_provider_down(bot, failed_regions, last_provider_error, today)


async def _notify_provider_down(
    bot: Bot, failed_regions: list[str], error: str, today: date,
) -> None:
    """Namoz vaqti manbai ishlamaganda adminlarga xabar yuboradi."""
    shown = failed_regions[:15]
    region_lines = "\n".join(f"• {escape_html(name)}" for name in shown)
    if len(failed_regions) > len(shown):
        region_lines += f"\n• …va yana {len(failed_regions) - len(shown)} ta"

    text = (
        "⚠️ <b>Namoz vaqti manbai ishlamadi</b>\n\n"
        f"📅 {today.isoformat()} — quyidagi <b>{len(failed_regions)}</b> hudud "
        "uchun kunlik post <b>yuborilmadi</b> (manba javob bermadi):\n"
        f"{region_lines}\n\n"
        f"🛑 Sabab: <code>{escape_html(error)}</code>\n\n"
        "ℹ️ Zaxira manba o'chirilgan (faqat islomapi). Manba tuzalgach "
        "postlar avtomatik tiklanadi. Zaxirani yoqish uchun: "
        "<code>PRAYER_PROVIDER_FALLBACK_ENABLED=true</code>"
    )
    await notify_admins(bot, text)


__all__ = ["run_daily_post"]
