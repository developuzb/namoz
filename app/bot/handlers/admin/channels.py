"""Admin: kanal CRUD (qo'shish/o'chirish/toggle).

Qo'shish flow (FSM):
  1. /admin → 📢 Kanallar → ➕ Yangi
  2. Bot kanaldan biror xabar forward qilishni so'raydi
  3. Forward kelsa — chat_id va title olinadi
  4. Hudud tanlash (viloyat → tuman, yoki flat list)
  5. Saqlanadi
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters import AdminFilter
from app.bot.keyboards import (
    admin_flat_picker,
    admin_panel_keyboard,
    admin_tuman_picker,
    admin_viloyat_picker,
    channel_delete_confirm_keyboard,
    channel_detail_keyboard,
    channels_list_keyboard,
)
from app.bot.keyboards.callback_data import (
    CB_ADMIN_CHANNELS,
    CB_ADMIN_ROOT,
    CB_CH_ADD,
    CB_CH_BACK_VIL,
    CB_CH_CANCEL,
    CB_CH_DELETE,
    CB_CH_DELETE_OK,
    CB_CH_TOGGLE,
    CB_CH_TUMAN,
    CB_CH_VIEW,
    CB_CH_VILOYAT,
)
from app.bot.states.admin import ChannelFSM
from app.core.exceptions import AlreadyExistsError
from app.core.logger import logger
from app.db.repositories.channel_repo import ChannelRepository
from app.db.repositories.region_repo import RegionRepository
from app.utils.text_utils import escape_html, normalize_channel_link

router = Router(name="admin.channels")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


# =================== List view ===================

async def _show_channels_list(
    message_or_call: Message | CallbackQuery,
    session: AsyncSession,
    *,
    edit: bool = True,
) -> None:
    ch_repo = ChannelRepository(session)
    channels = await ch_repo.list_all()
    # region eager load — bittadan
    rr = RegionRepository(session)
    for ch in channels:
        if ch.region is None and ch.region_id:
            ch.region = await rr.get(ch.region_id)

    if not channels:
        text = (
            "📢 <b>Kanallar</b>\n\n"
            "Hozircha kanal yo'q. Qo'shish uchun pastdagi tugmani bosing."
        )
    else:
        lines = ["📢 <b>Kanallar</b>", ""]
        for ch in channels:
            mark = "✅" if ch.is_active else "⏸"
            region_name = ch.region.name if ch.region else f"id={ch.region_id}"
            link = normalize_channel_link(ch.link) or f"chat_id=<code>{ch.chat_id}</code>"
            lines.append(f"{mark} <b>{escape_html(region_name)}</b>")
            lines.append(f"   {link}")
        text = "\n".join(lines)

    kb = channels_list_keyboard(channels)

    if isinstance(message_or_call, CallbackQuery):
        if edit:
            await message_or_call.message.edit_text(text, reply_markup=kb)
        else:
            await message_or_call.message.answer(text, reply_markup=kb)
        await message_or_call.answer()
    else:
        await message_or_call.answer(text, reply_markup=kb)


@router.callback_query(F.data == CB_ADMIN_CHANNELS)
async def show_channels(
    call: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    await state.clear()
    await _show_channels_list(call, session)


# =================== Add flow ===================

@router.callback_query(F.data == CB_CH_ADD)
async def start_add_channel(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ChannelFSM.waiting_forward)
    await call.message.edit_text(
        "📢 <b>Yangi kanal qo'shish</b>\n\n"
        "1️⃣ Botni o'sha kanalga <b>admin</b> sifatida qo'shing "
        "(post yuborish ruxsati bilan)\n"
        "2️⃣ Keyin shu yerga kanaldan <b>biror xabar forward qiling</b>\n\n"
        "Bekor qilish: /cancel"
    )
    await call.answer()


@router.message(StateFilter(ChannelFSM.waiting_forward), F.forward_from_chat)
async def receive_forwarded(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    chat = message.forward_from_chat
    if chat.type != "channel":
        await message.answer(
            "❌ Bu kanal emas (chat turi: <code>{}</code>).\n"
            "Iltimos, kanaldan forward qiling.".format(chat.type)
        )
        return

    # DB'da bunday chat_id bormi tekshiramiz
    ch_repo = ChannelRepository(session)
    existing = await ch_repo.get_by_chat_id(chat.id)
    if existing is not None:
        await message.answer(
            f"⚠️ Bu kanal allaqachon ro'yxatda: <code>{escape_html(chat.title or '')}</code>"
        )
        await state.clear()
        return

    # Kanal ma'lumotlarini state'ga saqlaymiz
    await state.update_data(
        chat_id=chat.id,
        title=chat.title or "",
        link=f"@{chat.username}" if chat.username else None,
    )
    await state.set_state(ChannelFSM.choosing_region)

    await _show_region_picker_for_channel(message, session)


@router.message(StateFilter(ChannelFSM.waiting_forward))
async def waiting_forward_invalid(message: Message) -> None:
    """Forward emas, oddiy matn kelganda yo'naltirish."""
    if message.text and message.text.startswith("/"):
        return  # /cancel singari komandalar
    await message.answer(
        "🔁 Forward kerak. Kanaldagi biror xabarni shu chatga forward qiling.\n"
        "Bekor qilish: /cancel"
    )


async def _show_region_picker_for_channel(
    target: Message, session: AsyncSession
) -> None:
    """Bosqich 1: viloyatlar va flat regionlar (lokatsiya orqali)."""
    rr = RegionRepository(session)
    top = await rr.list_top_level()

    # Viloyat (children'li) va flat (children'siz) ni ajratamiz
    parent_only = []
    flat_only = []
    for r in top:
        children = await rr.list_children(r.id)
        if children:
            parent_only.append(r)
        else:
            flat_only.append(r)

    if not parent_only and not flat_only:
        await target.answer("⚠️ DB'da region yo'q.")
        return

    text = (
        "📍 <b>Hududni tanlang</b>\n\n"
        "Kanal qaysi hudud uchun namoz vaqtlarini joylashtiradi?"
    )
    if parent_only:
        await target.answer(text, reply_markup=admin_viloyat_picker(parent_only))
    else:
        await target.answer(text, reply_markup=admin_flat_picker(flat_only))


@router.callback_query(
    StateFilter(ChannelFSM.choosing_region), F.data.startswith(f"{CB_CH_VILOYAT}:")
)
async def pick_viloyat(
    call: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    try:
        viloyat_id = int(call.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await call.answer("Noto'g'ri", show_alert=True)
        return

    rr = RegionRepository(session)
    children = await rr.list_children(viloyat_id)
    viloyat = await rr.get(viloyat_id)

    if not children:
        # Flat region — to'g'ridan-to'g'ri tanlanadi
        await _save_channel(call, state, session, region_id=viloyat_id)
        return

    text = f"📍 <b>{escape_html(viloyat.name)}</b>\nTumanni tanlang:"
    await call.message.edit_text(text, reply_markup=admin_tuman_picker(children))
    await call.answer()


@router.callback_query(
    StateFilter(ChannelFSM.choosing_region), F.data == CB_CH_BACK_VIL
)
async def back_to_viloyat(
    call: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    rr = RegionRepository(session)
    top = await rr.list_top_level()
    parent_only = []
    flat_only = []
    for r in top:
        children = await rr.list_children(r.id)
        (parent_only if children else flat_only).append(r)

    text = "📍 <b>Hududni tanlang</b>"
    if parent_only:
        await call.message.edit_text(text, reply_markup=admin_viloyat_picker(parent_only))
    else:
        await call.message.edit_text(text, reply_markup=admin_flat_picker(flat_only))
    await call.answer()


@router.callback_query(
    StateFilter(ChannelFSM.choosing_region), F.data.startswith(f"{CB_CH_TUMAN}:")
)
async def pick_tuman(
    call: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    try:
        tuman_id = int(call.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await call.answer("Noto'g'ri", show_alert=True)
        return

    await _save_channel(call, state, session, region_id=tuman_id)


@router.callback_query(StateFilter(ChannelFSM), F.data == CB_CH_CANCEL)
async def cancel_add(
    call: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    await state.clear()
    await call.answer("Bekor qilindi")
    await _show_channels_list(call, session)


@router.message(Command("cancel"), StateFilter(ChannelFSM))
async def cancel_via_command(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    await state.clear()
    await message.answer("❌ Bekor qilindi.")
    await _show_channels_list(message, session, edit=False)


async def _save_channel(
    call: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    *,
    region_id: int,
) -> None:
    data = await state.get_data()
    chat_id = data.get("chat_id")
    title = data.get("title")
    link = data.get("link")

    if not chat_id:
        await call.answer("Sessiya tugadi, qaytadan boshlang", show_alert=True)
        await state.clear()
        return

    ch_repo = ChannelRepository(session)
    rr = RegionRepository(session)
    region = await rr.get(region_id)
    if region is None:
        await call.answer("Region topilmadi", show_alert=True)
        return

    try:
        channel = await ch_repo.create(
            region_id=region_id,
            chat_id=chat_id,
            link=link,
            title=title,
            is_active=True,
        )
    except AlreadyExistsError as e:
        await call.answer(f"Xato: {e}", show_alert=True)
        await state.clear()
        return

    await state.clear()
    logger.info(
        "📢 Yangi kanal: id={} chat_id={} region={} title={!r}",
        channel.id, chat_id, region.name, title,
    )

    await call.message.edit_text(
        f"✅ <b>Kanal qo'shildi</b>\n\n"
        f"📢 <b>{escape_html(title or '')}</b>\n"
        f"🆔 <code>{chat_id}</code>\n"
        f"📍 {escape_html(region.name)}",
        reply_markup=channel_detail_keyboard(channel.id, is_active=True),
    )
    await call.answer("✅ Saqlandi")


# =================== View / toggle / delete ===================

@router.callback_query(F.data.startswith(f"{CB_CH_VIEW}:"))
async def view_channel(call: CallbackQuery, session: AsyncSession) -> None:
    try:
        ch_id = int(call.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await call.answer("Noto'g'ri", show_alert=True)
        return

    ch_repo = ChannelRepository(session)
    rr = RegionRepository(session)
    ch = await ch_repo.get(ch_id)
    if ch is None:
        await call.answer("Kanal topilmadi", show_alert=True)
        return
    region = await rr.get(ch.region_id)

    text = (
        f"📢 <b>{escape_html(ch.title or '—')}</b>\n\n"
        f"🆔 <code>{ch.chat_id}</code>\n"
        f"📍 {escape_html(region.name if region else '?')}\n"
        f"🔗 {escape_html(ch.link or '—')}\n"
        f"📊 {'✅ Faol' if ch.is_active else '⏸ Pauza'}"
    )
    await call.message.edit_text(
        text, reply_markup=channel_detail_keyboard(ch.id, ch.is_active),
    )
    await call.answer()


@router.callback_query(F.data.startswith(f"{CB_CH_TOGGLE}:"))
async def toggle_channel(call: CallbackQuery, session: AsyncSession) -> None:
    try:
        ch_id = int(call.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await call.answer("Noto'g'ri", show_alert=True)
        return

    ch_repo = ChannelRepository(session)
    ch = await ch_repo.get(ch_id)
    if ch is None:
        await call.answer("Kanal topilmadi", show_alert=True)
        return

    ch.is_active = not ch.is_active
    await session.flush()
    logger.info("Channel toggle: id={} is_active={}", ch_id, ch.is_active)
    await call.answer(
        "▶ Faollashtirildi" if ch.is_active else "⏸ Pauza qilindi"
    )
    await view_channel(call, session)


@router.callback_query(F.data.startswith(f"{CB_CH_DELETE}:"))
async def confirm_delete(call: CallbackQuery, session: AsyncSession) -> None:
    try:
        ch_id = int(call.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await call.answer("Noto'g'ri", show_alert=True)
        return

    ch_repo = ChannelRepository(session)
    ch = await ch_repo.get(ch_id)
    if ch is None:
        await call.answer("Kanal topilmadi", show_alert=True)
        return

    await call.message.edit_text(
        f"⚠️ <b>{escape_html(ch.title or '')}</b> kanalini DB'dan o'chirasizmi?\n\n"
        "<i>Kanal o'zi yo'q bo'lib ketmaydi — faqat bot ushbu kanalga "
        "post yubormay qo'yadi.</i>",
        reply_markup=channel_delete_confirm_keyboard(ch.id),
    )
    await call.answer()


@router.callback_query(F.data.startswith(f"{CB_CH_DELETE_OK}:"))
async def do_delete(call: CallbackQuery, session: AsyncSession) -> None:
    try:
        ch_id = int(call.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await call.answer("Noto'g'ri", show_alert=True)
        return

    ch_repo = ChannelRepository(session)
    ch = await ch_repo.get(ch_id)
    if ch is None:
        await call.answer("Kanal topilmadi", show_alert=True)
        return

    await ch_repo.delete(ch)
    logger.info("Channel deleted: id={}", ch_id)
    await call.answer("🗑 O'chirildi")
    await _show_channels_list(call, session)


# =================== Back to admin root ===================

@router.callback_query(F.data == CB_ADMIN_ROOT)
async def back_to_admin_root(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(
        "👑 <b>Admin paneli</b>\n\nQuyidagilardan birini tanlang:",
        reply_markup=admin_panel_keyboard(),
    )
    await call.answer()
