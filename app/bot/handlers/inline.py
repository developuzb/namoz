"""Inline mode handler — `@bot <region_name>` → namoz vaqtlari.

Telegram'da bot inline mode @BotFather dan yoqilishi kerak (`/setinline`).
Bu kod inline_query event'ini qabul qilib, hududlarni qidirib, har biri uchun
qisqacha namoz vaqtlari bilan InlineQueryResultArticle qaytaradi.
"""
from __future__ import annotations

from datetime import date

from aiogram import Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ALL_PRAYERS
from app.core.exceptions import ProviderError
from app.core.logger import logger
from app.db.models.region import Region
from app.services.registry import get_prayer_service
from app.utils.text_utils import escape_html

router = Router(name="inline")

#: Bir inline query'da maks natijalar
_MAX_RESULTS = 5


@router.inline_query()
async def inline_search(
    query: InlineQuery, session: AsyncSession
) -> None:
    q = (query.query or "").strip()
    if not q or len(q) < 2:
        # Bo'sh yoki juda qisqa — bo'sh natija (Telegram "Type to search" ko'rsatadi)
        await query.answer(
            results=[], cache_time=10, is_personal=False,
        )
        return

    # DB'da qidiruv (search.py'dagi bilan bir xil mantiq)
    stmt = (
        select(Region)
        .where(
            Region.is_active.is_(True),
            Region.name.ilike(f"%{q}%"),
        )
        .order_by(Region.name)
        .limit(_MAX_RESULTS)
    )
    result = await session.execute(stmt)
    regions = list(result.scalars().all())

    if not regions:
        # Hech narsa topilmadi — qisqa info qaytaramiz
        empty = InlineQueryResultArticle(
            id="empty",
            title=f"😔 \"{q}\" bo'yicha hudud topilmadi",
            description="Boshqa nom yuboring (Toshkent, Qarshi, Madinah...)",
            input_message_content=InputTextMessageContent(
                message_text=(
                    f"🔍 \"{escape_html(q)}\" bo'yicha hudud yo'q. "
                    f"To'liq botni @{(await query.bot.get_me()).username} dan oching."
                ),
            ),
        )
        await query.answer(results=[empty], cache_time=10, is_personal=False)
        return

    # Har region uchun bitta natija
    today = date.today()
    service = get_prayer_service()
    results: list[InlineQueryResultArticle] = []

    for r in regions:
        try:
            pt = await service.fetch_for_region(r, today)
        except ProviderError:
            continue

        # Qisqa caption — har vaqt yangi qatorda
        lines = [f"🕌 <b>{escape_html(r.name)}</b> — {today:%d.%m.%Y}", ""]
        for prayer in ALL_PRAYERS:
            t = pt.times.get(prayer, "—")
            lines.append(f"  • {prayer}: <code>{t}</code>")
        message_text = "\n".join(lines)

        # Description — qisqa ko'rinish
        farz_summary = " · ".join(
            pt.times.get(p, "—") for p in ("Bomdod", "Peshin", "Asr", "Shom", "Xufton")
        )
        results.append(
            InlineQueryResultArticle(
                id=f"r{r.id}",
                title=f"🕌 {r.name}" + (f" ({r.country})" if r.country else ""),
                description=farz_summary,
                input_message_content=InputTextMessageContent(
                    message_text=message_text,
                    parse_mode="HTML",
                ),
            )
        )

    if not results:
        # Provider barchasi xato bergan
        await query.answer(
            results=[
                InlineQueryResultArticle(
                    id="prov_fail",
                    title="⚠️ Vaqtlar olinmadi",
                    description="Provider hozir mavjud emas. Qaytadan urinib ko'ring.",
                    input_message_content=InputTextMessageContent(
                        message_text="⚠️ Namoz vaqtlari hozir mavjud emas.",
                    ),
                ),
            ],
            cache_time=30, is_personal=False,
        )
        return

    await query.answer(
        results=results,
        cache_time=300,  # 5 daqiqa cache (Telegram tomonida)
        is_personal=False,
    )
    logger.info("Inline query: q={!r} → {} results", q, len(results))
