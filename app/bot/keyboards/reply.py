"""Reply keyboard'lar — request_location, request_contact uchun."""
from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove


def location_request_keyboard() -> ReplyKeyboardMarkup:
    """Lokatsiyani so'raydigan reply keyboard.

    `request_location=True` Telegram'da native dialog ochadi —
    foydalanuvchi GPS yoki manual lokatsiya bera oladi.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Lokatsiyani yuborish", request_location=True)],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="📍 tugmani bosing yoki bekor qiling",
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    """Joriy reply keyboard'ni olib tashlaydi."""
    return ReplyKeyboardRemove()


__all__ = ["location_request_keyboard", "remove_keyboard"]
