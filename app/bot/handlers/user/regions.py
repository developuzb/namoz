"""Hudud tanlash va obuna toggle."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import tuman_keyboard, viloyat_keyboard
from app.bot.keyboards.callback_data import (
    CB_BACK_VILOYAT,
    CB_SELECT_REGION,
    CB_TUMAN,
    CB_VILOYAT,
)
from app.core.constants import MAX_SUBSCRIPTIONS_PER_USER
from app.core.logger import logger
from app.db.models.user import User
from app.db.repositories.region_repo import RegionRepository
from app.db.repositories.stats_repo import StatsRepository
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.utils.text_utils import escape_html

router = Router(name="user.regions")


async def _show_viloyat_list(call: CallbackQuery, session: AsyncSession) -> None:
    """Faqat haqiqiy viloyatlarni ko'rsatadi (sub-regionlari bor parent_id IS NULL)."""
    rr = RegionRepository(session)
    top_level = await rr.list_top_level()
    # Lokatsiya orqali yaratilgan flat shaharlarni chiqarib tashlaymiz
    viloyatlar = []
    for v in top_level:
        children = await rr.list_children(v.id)
        if children:
            viloyatlar.append(v)

    if not viloyatlar:
        await call.answer("Hozircha viloyatlar yo'q", show_alert=True)
        return

    await call.message.edit_text(
        "📍 <b>Viloyatni tanlang:</b>",
        reply_markup=viloyat_keyboard(viloyatlar),
    )
    await call.answer()


async def _show_tuman_list(
    call: CallbackQuery,
    user: User,
    session: AsyncSession,
    viloyat_id: int,
) -> None:
    rr = RegionRepository(session)
    sub_repo = SubscriptionRepository(session)

    viloyat = await rr.get(viloyat_id)
    if not viloyat:
        await call.answer("Viloyat topilmadi", show_alert=True)
        return

    tumanlar = await rr.list_children(viloyat_id)
    user_subs = await sub_repo.list_by_user(user.id)
    subscribed_ids = {s.region_id for s in user_subs}

    text = (
        f"📍 <b>{escape_html(viloyat.name)}</b>\n\n"
        f"Obunalar: <b>{len(user_subs)}/{MAX_SUBSCRIPTIONS_PER_USER}</b>\n"
        "Tugmani bossangiz obuna toggle qilinadi."
    )
    await call.message.edit_text(
        text,
        reply_markup=tuman_keyboard(tumanlar, subscribed_ids=subscribed_ids),
    )
    await call.answer()


@router.callback_query(F.data == CB_SELECT_REGION)
async def select_region(call: CallbackQuery) -> None:
    """Asosiy menyu'dan «Hudud tanlash» — onboarding 2 variantni ko'rsatadi."""
    from app.bot.keyboards import onboarding_keyboard

    await call.message.edit_text(
        "📍 Yangi hudud qo'shish:",
        reply_markup=onboarding_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data == CB_BACK_VILOYAT)
async def back_to_viloyat(call: CallbackQuery, session: AsyncSession) -> None:
    await _show_viloyat_list(call, session)


@router.callback_query(F.data.startswith(f"{CB_VILOYAT}:"))
async def open_viloyat(
    call: CallbackQuery, user: User, session: AsyncSession
) -> None:
    try:
        viloyat_id = int(call.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await call.answer("Noto'g'ri tugma", show_alert=True)
        return

    await _show_tuman_list(call, user, session, viloyat_id)


@router.callback_query(F.data.startswith(f"{CB_TUMAN}:"))
async def toggle_tuman(
    call: CallbackQuery, user: User, session: AsyncSession
) -> None:
    try:
        tuman_id = int(call.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await call.answer("Noto'g'ri tugma", show_alert=True)
        return

    rr = RegionRepository(session)
    sub_repo = SubscriptionRepository(session)
    stats = StatsRepository(session)

    tuman = await rr.get(tuman_id)
    if not tuman or tuman.parent_id is None:
        await call.answer("Tuman topilmadi", show_alert=True)
        return

    existing = await sub_repo.get_one(user.id, tuman_id)

    if existing:
        await sub_repo.delete(existing)
        await stats.track("unsubscribe", user_id=user.id, region_id=tuman_id)
        await call.answer(f"❌ {tuman.name} obunasi bekor qilindi")
        logger.info("Unsubscribe: tg_id={} region={}", user.tg_id, tuman.name)
    else:
        sub_count = await sub_repo.count_by_user(user.id)
        if sub_count >= MAX_SUBSCRIPTIONS_PER_USER:
            await call.answer(
                f"⛔ Sizda allaqachon {MAX_SUBSCRIPTIONS_PER_USER} ta obuna bor.\n"
                "Yangisini qo'shish uchun bittasidan voz keching.",
                show_alert=True,
            )
            return

        await sub_repo.create(user_id=user.id, region_id=tuman_id)
        await stats.track("subscribe", user_id=user.id, region_id=tuman_id)
        await call.answer(f"✅ {tuman.name} ga obuna bo'ldingiz")
        logger.info("Subscribe: tg_id={} region={}", user.tg_id, tuman.name)

    # Tuman ro'yxatini yangilash (✅ belgilarni qayta chizish)
    await _show_tuman_list(call, user, session, tuman.parent_id)
