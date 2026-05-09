"""Hudud nomini qidirish — DB'da case-insensitive substring match."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import location_confirm_keyboard, onboarding_keyboard
from app.bot.keyboards.callback_data import CB_LOC_CANCEL, CB_ONBOARD_SEARCH
from app.bot.states.admin import SearchFSM
from app.core.logger import logger
from app.db.models.region import Region
from app.utils.text_utils import escape_html

router = Router(name="user.search")

#: Bir qidiruvda max nechta natija ko'rsatiladi
_MAX_RESULTS = 10


@router.callback_query(F.data == CB_ONBOARD_SEARCH)
async def start_search(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SearchFSM.querying)
    await call.message.edit_text(
        "🔍 <b>Hudud qidirish</b>\n\n"
        "Hudud nomini yuboring (masalan: <code>Toshkent</code>, "
        "<code>Qarshi</code>, <code>Madinah</code>).\n\n"
        "Bekor qilish: /cancel"
    )
    await call.answer()


@router.message(StateFilter(SearchFSM.querying))
async def receive_query(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    if not message.text or message.text.startswith("/"):
        return

    query = message.text.strip()
    if len(query) < 2:
        await message.answer(
            "❌ So'rov juda qisqa. Kamida 2 belgi yuboring."
        )
        return

    # Case-insensitive substring match (SQLite)
    stmt = (
        select(Region)
        .where(
            Region.is_active.is_(True),
            Region.name.ilike(f"%{query}%"),
        )
        .order_by(Region.name)
        .limit(_MAX_RESULTS)
    )
    result = await session.execute(stmt)
    regions = result.scalars().all()

    if not regions:
        await message.answer(
            f"😔 <b>{escape_html(query)}</b> bo'yicha hech qanday hudud topilmadi.\n\n"
            "Boshqa nom yuboring yoki <i>📍 Lokatsiya orqali</i> tanlang.",
            reply_markup=onboarding_keyboard(),
        )
        await state.clear()
        return

    await state.clear()

    # Bitta natija — to'g'ridan-to'g'ri tasdiqlash so'raymiz
    if len(regions) == 1:
        r = regions[0]
        country = f", {escape_html(r.country)}" if r.country else ""
        await message.answer(
            f"✅ Topildi: <b>{escape_html(r.name)}</b>{country}\n\n"
            "Obuna bo'lasizmi?",
            reply_markup=location_confirm_keyboard(r.id),
        )
        logger.info("Search: tg_id=? query={!r} -> 1 match: {}", query, r.name)
        return

    # Bir nechta natija — har biri uchun tugma
    kb = InlineKeyboardBuilder()
    for r in regions:
        from app.bot.keyboards.callback_data import CB_LOC_CONFIRM
        country = f" ({r.country})" if r.country else ""
        kb.button(
            text=f"📍 {r.name}{country}",
            callback_data=f"{CB_LOC_CONFIRM}:{r.id}",
        )
    kb.button(text="❌ Boshqa qidiruv", callback_data=CB_LOC_CANCEL)
    kb.adjust(1)

    await message.answer(
        f"🔍 <b>{escape_html(query)}</b> bo'yicha <b>{len(regions)}</b> ta natija:",
        reply_markup=kb.as_markup(),
    )
    logger.info("Search: query={!r} -> {} matches", query, len(regions))
