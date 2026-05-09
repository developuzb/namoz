"""Admin: masjid (jamoat) namoz vaqtlarini hudud bo'yicha tahrirlash.

FSM oqim:
  1. /admin → 🕌 Masjid vaqtlari → viloyat tanlash
  2. (ixtiyoriy) → tuman tanlash
  3. 5 farz tugma → biriga bosish → vaqt so'raladi
  4. User HH:MM yuboradi → validation → upsert
  5. Avtomatik 5 farz ro'yxatiga qaytadi (yangilangan vaqt bilan)
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters import AdminFilter
from app.bot.keyboards import (
    admin_panel_keyboard,
    mt_cancel_keyboard,
    mt_flat_picker,
    mt_prayer_picker,
    mt_tuman_picker,
    mt_viloyat_picker,
)
from app.bot.keyboards.callback_data import (
    CB_ADMIN_MASJID,
    CB_ADMIN_ROOT,
    CB_MT_BACK_VIL,
    CB_MT_CANCEL,
    CB_MT_PRAYER,
    CB_MT_TUMAN,
    CB_MT_VILOYAT,
)
from app.bot.states.admin import MasjidTimeFSM
from app.core.constants import FARZ_PRAYERS
from app.core.logger import logger
from app.db.models.user import User
from app.db.repositories.masjid_time_repo import MasjidTimeRepository
from app.db.repositories.region_repo import RegionRepository
from app.utils.text_utils import escape_html
from app.utils.time_utils import clean_hhmm

router = Router(name="admin.masjid_times")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


# =================== Entry: viloyat list ===================

async def _show_region_picker(
    target: Message | CallbackQuery, session: AsyncSession, *, edit: bool = True
) -> None:
    """Faqat masjid jamoat vaqtlari bo'lgan viloyatlarni ko'rsatadi.

    Qoida: parent (viloyat)ning praytime_id yo'q (parent-only) lekin
    children'lari bor — masjid jamoat vaqtlari shunday tuzilishdagi
    UZ viloyatlar uchun mantiqli (hozirda faqat Qashqadaryo).
    Lokatsiya orqali yaratilgan flat regionlar bu yerda chiqmaydi.
    """
    rr = RegionRepository(session)
    top = await rr.list_top_level()
    parent_only: list = []
    for r in top:
        children = await rr.list_children(r.id)
        if children:
            parent_only.append(r)

    if not parent_only:
        text = "⚠️ Masjid jamoat vaqtlari biriktirilgan viloyat yo'q."
        if isinstance(target, CallbackQuery):
            await target.answer(text, show_alert=True)
        else:
            await target.answer(text)
        return

    text = (
        "🕌 <b>Masjid vaqtlari</b>\n\n"
        "Qaysi viloyat uchun jamoat vaqtlarini tahrirlamoqchisiz?\n\n"
        "<i>Masjid jamoat vaqtlari faqat O'zbekiston viloyatlari uchun "
        "qo'llaniladi. Lokatsiya orqali qo'shilgan hududlarda bu ustun "
        "ko'rsatilmaydi.</i>"
    )
    kb = mt_viloyat_picker(parent_only)

    if isinstance(target, CallbackQuery):
        if edit:
            await target.message.edit_text(text, reply_markup=kb)
        else:
            await target.message.answer(text, reply_markup=kb)
        await target.answer()
    else:
        await target.answer(text, reply_markup=kb)


@router.callback_query(F.data == CB_ADMIN_MASJID)
async def show_regions(
    call: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    await state.set_state(MasjidTimeFSM.choosing_region)
    await _show_region_picker(call, session)


# =================== Viloyat → tuman ===================

@router.callback_query(
    StateFilter(MasjidTimeFSM.choosing_region), F.data.startswith(f"{CB_MT_VILOYAT}:")
)
async def pick_viloyat(call: CallbackQuery, session: AsyncSession) -> None:
    try:
        viloyat_id = int(call.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await call.answer("Noto'g'ri", show_alert=True)
        return

    rr = RegionRepository(session)
    children = await rr.list_children(viloyat_id)
    viloyat = await rr.get(viloyat_id)

    if not children:
        # Flat — to'g'ridan-to'g'ri prayer picker'ga
        await _show_prayers_for_region(call, session, region_id=viloyat_id)
        return

    text = f"📍 <b>{escape_html(viloyat.name)}</b>\nTumanni tanlang:"
    await call.message.edit_text(text, reply_markup=mt_tuman_picker(children))
    await call.answer()


@router.callback_query(
    StateFilter(MasjidTimeFSM.choosing_region), F.data == CB_MT_BACK_VIL
)
async def back_to_viloyats(
    call: CallbackQuery, session: AsyncSession
) -> None:
    await _show_region_picker(call, session)


# =================== Tuman / flat → 5 farz ===================

@router.callback_query(F.data.startswith(f"{CB_MT_TUMAN}:"))
async def pick_tuman(
    call: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    try:
        region_id = int(call.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await call.answer("Noto'g'ri", show_alert=True)
        return
    await _show_prayers_for_region(call, session, region_id=region_id)
    await state.set_state(MasjidTimeFSM.choosing_prayer)


async def _show_prayers_for_region(
    call: CallbackQuery, session: AsyncSession, *, region_id: int
) -> None:
    rr = RegionRepository(session)
    mr = MasjidTimeRepository(session)
    region = await rr.get(region_id)
    if region is None:
        await call.answer("Region topilmadi", show_alert=True)
        return

    current = await mr.get_for_region(region_id)

    text = (
        f"🕌 <b>{escape_html(region.name)}</b> — masjid vaqtlari\n\n"
        "Tahrirlash uchun namozga bosing:"
    )
    await call.message.edit_text(
        text, reply_markup=mt_prayer_picker(region_id, current),
    )
    await call.answer()


# =================== Prayer tanlandi → vaqt so'raladi ===================

@router.callback_query(F.data.startswith(f"{CB_MT_PRAYER}:"))
async def pick_prayer(
    call: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    try:
        _, region_id_str, prayer = call.data.split(":", 2)
        region_id = int(region_id_str)
    except (ValueError, IndexError):
        await call.answer("Noto'g'ri", show_alert=True)
        return

    if prayer not in FARZ_PRAYERS:
        await call.answer("Faqat farz vaqtlari", show_alert=True)
        return

    rr = RegionRepository(session)
    mr = MasjidTimeRepository(session)
    region = await rr.get(region_id)
    if region is None:
        await call.answer("Region topilmadi", show_alert=True)
        return

    current = await mr.get_for_region(region_id)
    current_time = current.get(prayer, "—")

    await state.update_data(region_id=region_id, prayer=prayer)
    await state.set_state(MasjidTimeFSM.entering_time)

    await call.message.edit_text(
        f"🕌 <b>{escape_html(region.name)}</b> — <b>{prayer}</b>\n\n"
        f"Hozirgi vaqt: <code>{current_time}</code>\n\n"
        "Yangi vaqtni HH:MM formatida yuboring (masalan, <code>17:35</code>).\n\n"
        "Yoki bekor qilish uchun pastdagi tugmani bosing.",
        reply_markup=mt_cancel_keyboard(),
    )
    await call.answer()


# =================== Vaqt qabul qilish ===================

@router.message(StateFilter(MasjidTimeFSM.entering_time))
async def receive_time(
    message: Message, session: AsyncSession, state: FSMContext, user: User
) -> None:
    if message.text and message.text.startswith("/"):
        return  # /cancel singari komandalar boshqa handler'ga

    cleaned = clean_hhmm(message.text)
    if cleaned is None:
        await message.answer(
            "❌ Vaqt formati noto'g'ri. <code>HH:MM</code> ko'rinishida yuboring "
            "(masalan, <code>17:35</code>).\n\n"
            "Yoki bekor qiling: /cancel"
        )
        return

    data = await state.get_data()
    region_id = data.get("region_id")
    prayer = data.get("prayer")
    if not region_id or not prayer:
        await state.clear()
        await message.answer("⚠️ Sessiya tugadi. Qaytadan boshlang: /admin")
        return

    mr = MasjidTimeRepository(session)
    rr = RegionRepository(session)

    await mr.upsert(
        region_id=region_id,
        prayer=prayer,
        time=cleaned,
        updated_by_tg_id=user.tg_id,
    )

    region = await rr.get(region_id)
    logger.info(
        "Masjid vaqti yangilandi: tg_id={} region={} {}={}",
        user.tg_id, region.name if region else region_id, prayer, cleaned,
    )

    await message.answer(
        f"✅ <b>{prayer}</b> vaqti <code>{cleaned}</code> qilib saqlandi."
    )

    # 5 farz tugmali ro'yxatga qaytaramiz
    current = await mr.get_for_region(region_id)
    await state.set_state(MasjidTimeFSM.choosing_prayer)
    await message.answer(
        f"🕌 <b>{escape_html(region.name if region else '?')}</b> — masjid vaqtlari\n\n"
        "Boshqa namozni ham tahrir qilishingiz mumkin:",
        reply_markup=mt_prayer_picker(region_id, current),
    )


# =================== Cancel ===================

@router.callback_query(StateFilter(MasjidTimeFSM), F.data == CB_MT_CANCEL)
async def cancel_via_button(
    call: CallbackQuery, state: FSMContext
) -> None:
    await state.clear()
    await call.message.edit_text(
        "❌ Bekor qilindi.\n\n👑 <b>Admin paneli</b>",
        reply_markup=admin_panel_keyboard(),
    )
    await call.answer()


@router.message(Command("cancel"), StateFilter(MasjidTimeFSM))
async def cancel_via_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "❌ Bekor qilindi.\n\n👑 <b>Admin paneli</b>",
        reply_markup=admin_panel_keyboard(),
    )
