"""Asosiy menyu callback (« Menu tugmasi)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import main_menu_keyboard, onboarding_keyboard
from app.bot.keyboards.callback_data import CB_MAIN_MENU
from app.db.models.user import User
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.utils.text_utils import escape_html

router = Router(name="user.menu")


@router.callback_query(F.data == CB_MAIN_MENU)
async def back_to_menu(
    call: CallbackQuery, user: User, session: AsyncSession
) -> None:
    sub_repo = SubscriptionRepository(session)
    sub_count = await sub_repo.count_by_user(user.id)
    has_subs = sub_count > 0

    name = escape_html(user.full_name or "birodar")
    if has_subs:
        text = (
            f"<b>{name}</b>, sizda <b>{sub_count}</b> ta obuna bor.\n"
            "Quyidagilardan birini tanlang:"
        )
        await call.message.edit_text(
            text, reply_markup=main_menu_keyboard(has_subscriptions=True),
        )
    else:
        text = (
            f"<b>{name}</b>, hozircha hech qaysi hududga obuna emassiz.\n"
            "Hududingizni qanday topamiz?"
        )
        await call.message.edit_text(text, reply_markup=onboarding_keyboard())
    await call.answer()
