"""Admin paneli uchun maxsus keyboardlar."""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

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
    CB_MT_BACK_VIL,
    CB_MT_CANCEL,
    CB_MT_PRAYER,
    CB_MT_TUMAN,
    CB_MT_VILOYAT,
)
from app.core.constants import FARZ_PRAYERS
from app.db.models.channel import Channel
from app.db.models.region import Region


def channels_list_keyboard(channels: list[Channel]) -> InlineKeyboardMarkup:
    """Mavjud kanallar ro'yxati + Yangi qo'shish tugmasi."""
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Yangi kanal qo'shish", callback_data=CB_CH_ADD)
    for ch in channels:
        mark = "✅" if ch.is_active else "⏸"
        region_name = ch.region.name if ch.region else f"id={ch.region_id}"
        kb.button(
            text=f"{mark} {region_name}",
            callback_data=f"{CB_CH_VIEW}:{ch.id}",
        )
    kb.button(text="« Admin paneli", callback_data=CB_ADMIN_ROOT)
    sizes = [1] + [1] * len(channels) + [1]
    kb.adjust(*sizes)
    return kb.as_markup()


def channel_detail_keyboard(channel_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Bitta kanal uchun amallar (toggle / delete / back)."""
    kb = InlineKeyboardBuilder()
    toggle_text = "⏸ Pauza" if is_active else "▶ Faollashtirish"
    kb.button(text=toggle_text, callback_data=f"{CB_CH_TOGGLE}:{channel_id}")
    kb.button(text="🗑 O'chirish", callback_data=f"{CB_CH_DELETE}:{channel_id}")
    kb.button(text="« Kanallar ro'yxati", callback_data=CB_ADMIN_CHANNELS)
    kb.adjust(2, 1)
    return kb.as_markup()


def channel_delete_confirm_keyboard(channel_id: int) -> InlineKeyboardMarkup:
    """O'chirishni tasdiqlash."""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Ha, o'chirish", callback_data=f"{CB_CH_DELETE_OK}:{channel_id}")
    kb.button(text="❌ Bekor", callback_data=f"{CB_CH_VIEW}:{channel_id}")
    kb.adjust(1)
    return kb.as_markup()


def admin_viloyat_picker(viloyatlar: list[Region]) -> InlineKeyboardMarkup:
    """Admin uchun viloyat tanlovchi (kanal qo'shish flow'ida)."""
    kb = InlineKeyboardBuilder()
    for v in viloyatlar:
        kb.button(text=f"📍 {v.name}", callback_data=f"{CB_CH_VILOYAT}:{v.id}")
    kb.button(text="❌ Bekor qilish", callback_data=CB_CH_CANCEL)
    kb.adjust(1)
    return kb.as_markup()


def admin_tuman_picker(tumanlar: list[Region]) -> InlineKeyboardMarkup:
    """Admin uchun tuman tanlovchi."""
    kb = InlineKeyboardBuilder()
    for t in tumanlar:
        kb.button(text=t.name, callback_data=f"{CB_CH_TUMAN}:{t.id}")
    kb.button(text="« Viloyatlar", callback_data=CB_CH_BACK_VIL)
    kb.button(text="❌ Bekor qilish", callback_data=CB_CH_CANCEL)
    sizes = [2] * ((len(tumanlar) + 1) // 2) + [1, 1]
    kb.adjust(*sizes)
    return kb.as_markup()


def admin_flat_picker(regions: list[Region]) -> InlineKeyboardMarkup:
    """Lokatsiya orqali yaratilgan flat regionlar (parent_id NULL, no children)."""
    kb = InlineKeyboardBuilder()
    for r in regions:
        kb.button(text=f"📍 {r.name}", callback_data=f"{CB_CH_TUMAN}:{r.id}")
    kb.button(text="« Viloyatlar", callback_data=CB_CH_BACK_VIL)
    kb.button(text="❌ Bekor qilish", callback_data=CB_CH_CANCEL)
    sizes = [2] * ((len(regions) + 1) // 2) + [1, 1]
    kb.adjust(*sizes)
    return kb.as_markup()


def mt_viloyat_picker(viloyatlar: list[Region]) -> InlineKeyboardMarkup:
    """Masjid vaqti uchun viloyat tanlovchi."""
    kb = InlineKeyboardBuilder()
    for v in viloyatlar:
        kb.button(text=f"📍 {v.name}", callback_data=f"{CB_MT_VILOYAT}:{v.id}")
    kb.button(text="« Admin paneli", callback_data=CB_ADMIN_ROOT)
    kb.adjust(1)
    return kb.as_markup()


def mt_tuman_picker(tumanlar: list[Region]) -> InlineKeyboardMarkup:
    """Masjid vaqti uchun tuman tanlovchi."""
    kb = InlineKeyboardBuilder()
    for t in tumanlar:
        kb.button(text=t.name, callback_data=f"{CB_MT_TUMAN}:{t.id}")
    kb.button(text="« Viloyatlar", callback_data=CB_MT_BACK_VIL)
    sizes = [2] * ((len(tumanlar) + 1) // 2) + [1]
    kb.adjust(*sizes)
    return kb.as_markup()


def mt_flat_picker(regions: list[Region]) -> InlineKeyboardMarkup:
    """Lokatsiya orqali yaratilgan flat regionlar uchun."""
    kb = InlineKeyboardBuilder()
    for r in regions:
        kb.button(text=f"📍 {r.name}", callback_data=f"{CB_MT_TUMAN}:{r.id}")
    kb.button(text="« Admin paneli", callback_data=CB_ADMIN_ROOT)
    sizes = [2] * ((len(regions) + 1) // 2) + [1]
    kb.adjust(*sizes)
    return kb.as_markup()


def mt_prayer_picker(
    region_id: int, current_times: dict[str, str]
) -> InlineKeyboardMarkup:
    """5 farz namoz uchun tugma — har birida hozirgi vaqt ko'rsatiladi."""
    kb = InlineKeyboardBuilder()
    for prayer in FARZ_PRAYERS:
        time_str = current_times.get(prayer, "—")
        kb.button(
            text=f"{prayer}: {time_str}",
            callback_data=f"{CB_MT_PRAYER}:{region_id}:{prayer}",
        )
    kb.button(text="« Hududlar", callback_data=CB_MT_BACK_VIL)
    kb.adjust(2, 2, 1, 1)  # 2x2 + Xufton + back
    return kb.as_markup()


def mt_cancel_keyboard() -> InlineKeyboardMarkup:
    """FSM oxirida bekor qilish tugmasi."""
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Bekor qilish", callback_data=CB_MT_CANCEL)
    return kb.as_markup()


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Broadcast yuborishni tasdiqlash."""
    from app.bot.keyboards.callback_data import CB_BC_CANCEL, CB_BC_CONFIRM

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Hammaga yuborish", callback_data=CB_BC_CONFIRM)
    kb.button(text="❌ Bekor qilish", callback_data=CB_BC_CANCEL)
    kb.adjust(1)
    return kb.as_markup()


__all__ = [
    "admin_flat_picker",
    "admin_tuman_picker",
    "admin_viloyat_picker",
    "broadcast_confirm_keyboard",
    "channel_delete_confirm_keyboard",
    "channel_detail_keyboard",
    "channels_list_keyboard",
    "mt_cancel_keyboard",
    "mt_flat_picker",
    "mt_prayer_picker",
    "mt_tuman_picker",
    "mt_viloyat_picker",
]
