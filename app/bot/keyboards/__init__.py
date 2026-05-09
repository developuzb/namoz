"""Inline va reply keyboard yasovchi funksiyalar."""
from app.bot.keyboards.admin_kb import (
    admin_flat_picker,
    admin_tuman_picker,
    admin_viloyat_picker,
    broadcast_confirm_keyboard,
    channel_delete_confirm_keyboard,
    channel_detail_keyboard,
    channels_list_keyboard,
    mt_cancel_keyboard,
    mt_flat_picker,
    mt_prayer_picker,
    mt_tuman_picker,
    mt_viloyat_picker,
)
from app.bot.keyboards.inline import (
    admin_panel_keyboard,
    location_confirm_keyboard,
    main_menu_keyboard,
    onboarding_keyboard,
    settings_keyboard,
    tuman_keyboard,
    viloyat_keyboard,
)
from app.bot.keyboards.reply import location_request_keyboard, remove_keyboard

__all__ = [
    "admin_flat_picker",
    "admin_panel_keyboard",
    "admin_tuman_picker",
    "admin_viloyat_picker",
    "broadcast_confirm_keyboard",
    "channel_delete_confirm_keyboard",
    "channel_detail_keyboard",
    "channels_list_keyboard",
    "location_confirm_keyboard",
    "location_request_keyboard",
    "main_menu_keyboard",
    "mt_cancel_keyboard",
    "mt_flat_picker",
    "mt_prayer_picker",
    "mt_tuman_picker",
    "mt_viloyat_picker",
    "onboarding_keyboard",
    "remove_keyboard",
    "settings_keyboard",
    "tuman_keyboard",
    "viloyat_keyboard",
]
