"""Botni do'stlarga yuborish — Telegram switch_inline_query bilan."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.bot.keyboards.callback_data import CB_MAIN_MENU, CB_SHARE

router = Router(name="user.share")


@router.callback_query(F.data == CB_SHARE)
async def share(call: CallbackQuery) -> None:
    me = await call.bot.get_me()
    bot_username = me.username
    deep_link = f"https://t.me/{bot_username}"

    # Telegram'ning switch_inline_query — chat ro'yxati ochiladi va mas tayyorlanadi
    share_text = (
        f"🕌 Men @nmsupportbot dan foydalanaman — "
        f"har kuni namoz vaqtlari, qibla yo'nalishi, hijriy sana va boshqa "
        f"foydali ma'lumotlar.\n\n{deep_link}"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Do'stlarga yuborish (chat tanlash)",
                    switch_inline_query=share_text,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔗 Linkni ko'chirish",
                    url=deep_link,
                )
            ],
            [
                InlineKeyboardButton(text="« Menu", callback_data=CB_MAIN_MENU),
            ],
        ]
    )
    text = (
        "📤 <b>Botni do'stlarga ulashing</b>\n\n"
        f"<b>Link:</b> <code>{deep_link}</code>\n\n"
        "<i>Pastdagi tugmadan istalgan chatga jo'natishingiz mumkin.</i>"
    )
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()
