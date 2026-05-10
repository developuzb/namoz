"""Inline keyboard yasovchi funksiyalar."""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.keyboards.callback_data import (
    CB_ADMIN_BROADCAST,
    CB_ADMIN_CHANNELS,
    CB_ADMIN_MASJID,
    CB_ADMIN_STATS,
    CB_ADMIN_TEST_POST,
    CB_BACK_VILOYAT,
    CB_LOC_CANCEL,
    CB_LOC_CONFIRM,
    CB_MAIN_MENU,
    CB_MY_TIMES,
    CB_NAFL_NOW,
    CB_NEXT_FARZ,
    CB_ONBOARD_LIST,
    CB_ONBOARD_LOCATION,
    CB_SELECT_REGION,
    CB_SETTINGS,
    CB_TOGGLE_DAILY,
    CB_TOGGLE_FARZ,
    CB_TOGGLE_NAFL,
    CB_TOGGLE_QUIET,
    CB_TUMAN,
    CB_VILOYAT,
)
from app.db.models.region import Region


def viloyat_keyboard(viloyatlar: list[Region]) -> InlineKeyboardMarkup:
    """Viloyatlar ro'yxati (bitta ustun)."""
    kb = InlineKeyboardBuilder()
    for v in viloyatlar:
        kb.button(text=f"📍 {v.name}", callback_data=f"{CB_VILOYAT}:{v.id}")
    kb.button(text="« Menu", callback_data=CB_MAIN_MENU)
    kb.adjust(1)
    return kb.as_markup()


def tuman_keyboard(
    tumanlar: list[Region],
    *,
    subscribed_ids: set[int] | None = None,
) -> InlineKeyboardMarkup:
    """Tumanlar ro'yxati. Obuna bo'lganlari ✅ bilan belgilanadi."""
    subs = subscribed_ids or set()
    kb = InlineKeyboardBuilder()
    for t in tumanlar:
        prefix = "✅ " if t.id in subs else ""
        kb.button(text=f"{prefix}{t.name}", callback_data=f"{CB_TUMAN}:{t.id}")
    kb.button(text="« Viloyatlar", callback_data=CB_BACK_VILOYAT)
    # 2 ustun tumanlar uchun, 1 qator orqaga tugmasi uchun
    sizes = [2] * ((len(tumanlar) + 1) // 2) + [1]
    kb.adjust(*sizes)
    return kb.as_markup()


def main_menu_keyboard(*, has_subscriptions: bool) -> InlineKeyboardMarkup:
    """Asosiy menyu — /start dan keyin yoki menyuga qaytishda."""
    from app.bot.keyboards.callback_data import (
        CB_QIBLA, CB_SHARE, CB_TOMORROW_TIMES,
    )

    kb = InlineKeyboardBuilder()
    if has_subscriptions:
        kb.button(text="🕌 Bugungi vaqtlar", callback_data=CB_MY_TIMES)
        kb.button(text="🌅 Ertangi vaqtlar", callback_data=CB_TOMORROW_TIMES)
        kb.button(text="⏭ Keyingi farz", callback_data=CB_NEXT_FARZ)
        kb.button(text="🌙 Hozir qaysi nafl?", callback_data=CB_NAFL_NOW)
        kb.button(text="🧭 Qibla yo'nalishi", callback_data=CB_QIBLA)
    kb.button(text="📍 Hudud tanlash", callback_data=CB_SELECT_REGION)
    kb.button(text="⚙️ Sozlamalar", callback_data=CB_SETTINGS)
    kb.button(text="📤 Botni do'stga yuborish", callback_data=CB_SHARE)

    if has_subscriptions:
        # [bugun|ertaga] [keyingi|nafl] [qibla] [hudud|sozlamalar] [share]
        kb.adjust(2, 2, 1, 2, 1)
    else:
        kb.adjust(1, 1, 1)
    return kb.as_markup()


def settings_keyboard(
    *, notify_farz: bool, notify_nafl: bool, daily_post: bool,
    quiet_hours: bool = False,
) -> InlineKeyboardMarkup:
    """Foydalanuvchi sozlamalari — toggle tugmalar."""
    kb = InlineKeyboardBuilder()

    def mark(flag: bool) -> str:
        return "✅" if flag else "⬜️"

    kb.button(
        text=f"{mark(notify_farz)} Farz vaqtida eslatma",
        callback_data=CB_TOGGLE_FARZ,
    )
    kb.button(
        text=f"{mark(notify_nafl)} Tahajjud eslatma",
        callback_data=CB_TOGGLE_NAFL,
    )
    kb.button(
        text=f"{mark(daily_post)} Kunlik post DM ga",
        callback_data=CB_TOGGLE_DAILY,
    )
    kb.button(
        text=f"{mark(quiet_hours)} 🌙 Tinch soatlar (23:00–05:00)",
        callback_data=CB_TOGGLE_QUIET,
    )
    kb.button(text="« Menu", callback_data=CB_MAIN_MENU)
    kb.adjust(1)
    return kb.as_markup()


def onboarding_keyboard() -> InlineKeyboardMarkup:
    """/start onboarding — 3 variant: lokatsiya / ro'yxat / qidirish."""
    from app.bot.keyboards.callback_data import CB_ONBOARD_SEARCH

    kb = InlineKeyboardBuilder()
    kb.button(
        text="📍 Lokatsiya orqali topish (tavsiya)",
        callback_data=CB_ONBOARD_LOCATION,
    )
    kb.button(text="🔍 Nomini qidirish", callback_data=CB_ONBOARD_SEARCH)
    kb.button(text="🗂 Ro'yxatdan tanlash", callback_data=CB_ONBOARD_LIST)
    kb.adjust(1)
    return kb.as_markup()


def location_confirm_keyboard(region_id: int) -> InlineKeyboardMarkup:
    """Geocode topilgan hududni tasdiqlash/bekor qilish."""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Obuna bo'lish", callback_data=f"{CB_LOC_CONFIRM}:{region_id}")
    kb.button(text="❌ Boshqa joy tanlash", callback_data=CB_LOC_CANCEL)
    kb.adjust(1)
    return kb.as_markup()


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Admin paneli asosiy menyu."""
    from app.bot.keyboards.callback_data import CB_ADMIN_REGIONS, CB_ADMIN_USERS

    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Statistika", callback_data=CB_ADMIN_STATS)
    kb.button(text="📢 Kanallar", callback_data=CB_ADMIN_CHANNELS)
    kb.button(text="📍 Hududlar", callback_data=CB_ADMIN_REGIONS)
    kb.button(text="👥 Foydalanuvchilar", callback_data=CB_ADMIN_USERS)
    kb.button(text="🕌 Masjid vaqtlari", callback_data=CB_ADMIN_MASJID)
    kb.button(text="📨 Broadcast", callback_data=CB_ADMIN_BROADCAST)
    kb.button(text="🧪 Test post", callback_data=CB_ADMIN_TEST_POST)
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()
