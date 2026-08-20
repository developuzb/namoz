"""Admin: hudud (region) CRUD — list / detail / toggle / delete."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters import AdminFilter
from app.bot.keyboards import admin_panel_keyboard
from app.bot.keyboards.callback_data import (
    CB_ADMIN_REGIONS,
    CB_ADMIN_ROOT,
    CB_RG_DELETE,
    CB_RG_DELETE_OK,
    CB_RG_TOGGLE_ACTIVE,
    CB_RG_VIEW,
)
from app.core.logger import logger
from app.db.models.region import Region
from app.db.repositories.region_repo import RegionRepository
from app.utils.text_utils import escape_html

router = Router(name="admin.regions")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


def _list_keyboard(regions: list[Region]):
    kb = InlineKeyboardBuilder()
    for r in regions:
        mark = "✅" if r.is_active else "⏸"
        kb.button(text=f"{mark} {r.name}", callback_data=f"{CB_RG_VIEW}:{r.id}")
    kb.button(text="« Admin paneli", callback_data=CB_ADMIN_ROOT)
    sizes = [1] * len(regions) + [1]
    kb.adjust(*sizes)
    return kb.as_markup()


def _detail_keyboard(region_id: int, is_active: bool):
    kb = InlineKeyboardBuilder()
    label = "⏸ Pauza qilish" if is_active else "▶ Faollashtirish"
    kb.button(text=label, callback_data=f"{CB_RG_TOGGLE_ACTIVE}:{region_id}")
    kb.button(text="🗑 O'chirish", callback_data=f"{CB_RG_DELETE}:{region_id}")
    kb.button(text="« Hududlar ro'yxati", callback_data=CB_ADMIN_REGIONS)
    kb.adjust(2, 1)
    return kb.as_markup()


def _confirm_delete_keyboard(region_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Ha, o'chirish", callback_data=f"{CB_RG_DELETE_OK}:{region_id}")
    kb.button(text="❌ Bekor", callback_data=f"{CB_RG_VIEW}:{region_id}")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == CB_ADMIN_REGIONS)
async def show_list(call: CallbackQuery, session: AsyncSession) -> None:
    stmt = select(Region).order_by(Region.parent_id.nulls_first(), Region.name)
    result = await session.execute(stmt)
    regions = list(result.scalars().all())

    if not regions:
        await call.message.edit_text(
            "📍 Hudud yo'q.",
            reply_markup=admin_panel_keyboard(),
        )
        await call.answer()
        return

    text = (
        f"📍 <b>Hududlar</b> (jami {len(regions)})\n\n"
        "<i>Tugmani bossangiz batafsil ma'lumot va amallar.</i>"
    )
    await call.message.edit_text(text, reply_markup=_list_keyboard(regions))
    await call.answer()


@router.callback_query(F.data.startswith(f"{CB_RG_VIEW}:"))
async def view_region(call: CallbackQuery, session: AsyncSession) -> None:
    try:
        rid = int(call.data.split(":")[-1])
    except (ValueError, IndexError):
        await call.answer("Noto'g'ri", show_alert=True)
        return

    rr = RegionRepository(session)
    r = await rr.get(rid)
    if r is None:
        await call.answer("Hudud topilmadi", show_alert=True)
        return

    parent = await rr.get(r.parent_id) if r.parent_id else None
    coords = (
        f"{r.latitude:.4f}, {r.longitude:.4f}"
        if r.latitude is not None and r.longitude is not None
        else "—"
    )
    providers = []
    if r.provider_name:
        providers.append(f"islomapi=<code>{escape_html(r.provider_name)}</code>")
    if r.praytime_id:
        providers.append(f"praytime_id={r.praytime_id}")
    if r.latitude and r.longitude:
        providers.append("aladhan=✓")

    text = (
        f"📍 <b>{escape_html(r.name)}</b>\n\n"
        f"🆔 ID: <code>{r.id}</code>\n"
        f"📛 Slug: <code>{escape_html(r.slug)}</code>\n"
        f"📌 Koordinata: <code>{coords}</code>\n"
        f"🌐 Timezone: <code>{escape_html(r.timezone)}</code>\n"
        f"🏛 Mamlakat: <code>{escape_html(r.country or '—')}</code>\n"
        f"👥 Parent: <code>{escape_html(parent.name) if parent else '—'}</code>\n"
        f"📊 Holat: {'✅ Faol' if r.is_active else '⏸ Pauza'}\n"
        f"🔌 Provider'lar: {' · '.join(providers) if providers else '—'}\n"
    )
    await call.message.edit_text(
        text, reply_markup=_detail_keyboard(r.id, r.is_active),
    )
    await call.answer()


@router.callback_query(F.data.startswith(f"{CB_RG_TOGGLE_ACTIVE}:"))
async def toggle_active(call: CallbackQuery, session: AsyncSession) -> None:
    try:
        rid = int(call.data.split(":")[-1])
    except (ValueError, IndexError):
        await call.answer("Noto'g'ri", show_alert=True)
        return

    rr = RegionRepository(session)
    r = await rr.get(rid)
    if r is None:
        await call.answer("Hudud topilmadi", show_alert=True)
        return

    r.is_active = not r.is_active
    await session.flush()
    logger.info("Region toggle: id={} is_active={}", rid, r.is_active)
    await call.answer("▶ Faollashtirildi" if r.is_active else "⏸ Pauza qilindi")
    await view_region(call, session)


@router.callback_query(F.data.startswith(f"{CB_RG_DELETE}:"))
async def confirm_delete(call: CallbackQuery, session: AsyncSession) -> None:
    try:
        rid = int(call.data.split(":")[-1])
    except (ValueError, IndexError):
        await call.answer("Noto'g'ri", show_alert=True)
        return

    rr = RegionRepository(session)
    r = await rr.get(rid)
    if r is None:
        await call.answer("Hudud topilmadi", show_alert=True)
        return

    await call.message.edit_text(
        f"⚠️ <b>{escape_html(r.name)}</b> hududini DB'dan o'chirasizmi?\n\n"
        "<i>CASCADE: bu hududning kanallari, masjid vaqtlari va "
        "obunalari ham o'chiriladi.</i>",
        reply_markup=_confirm_delete_keyboard(r.id),
    )
    await call.answer()


@router.callback_query(F.data.startswith(f"{CB_RG_DELETE_OK}:"))
async def do_delete(call: CallbackQuery, session: AsyncSession) -> None:
    try:
        rid = int(call.data.split(":")[-1])
    except (ValueError, IndexError):
        await call.answer("Noto'g'ri", show_alert=True)
        return

    rr = RegionRepository(session)
    r = await rr.get(rid)
    if r is None:
        await call.answer("Hudud topilmadi", show_alert=True)
        return

    name = r.name
    await rr.delete(r)
    logger.info("Region deleted: id={} name={!r}", rid, name)
    await call.answer(f"🗑 {name} o'chirildi")
    await show_list(call, session)
