"""Umumiy buyruqlar — global /cancel."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import main_menu_keyboard, remove_keyboard
from app.db.models.user import User
from app.db.repositories.subscription_repo import SubscriptionRepository

router = Router(name="user.common")


@router.message(Command("cancel"))
async def cmd_cancel(
    message: Message,
    state: FSMContext,
    user: User | None,
    session: AsyncSession,
) -> None:
    """Istalgan FSM holatini tozalaydi va asosiy menyuga qaytaradi.

    Subroyterlardagi /cancel handlerlari (admin/channels, admin/masjid_times,
    admin/broadcast) shu bilan bir vaqtda registered. Aiogram tartibga ko'ra
    ular avval ishlaydi (agar mos state bo'lsa). Bu handler — fallback.
    """
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()

    await message.answer(
        "❌ Bekor qilindi.",
        reply_markup=remove_keyboard(),
    )

    if user is None:
        return

    sub_repo = SubscriptionRepository(session)
    sub_count = await sub_repo.count_by_user(user.id)
    await message.answer(
        "Asosiy menyu:",
        reply_markup=main_menu_keyboard(has_subscriptions=sub_count > 0),
    )
