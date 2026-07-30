"""/start handler — onboarding va asosiy menyu."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import main_menu_keyboard, onboarding_keyboard
from app.core.logger import logger
from app.db.models.user import User
from app.db.repositories.stats_repo import StatsRepository
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.utils.text_utils import escape_html

router = Router(name="user.start")


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    user: User | None,
    is_admin: bool,
    session: AsyncSession,
) -> None:
    if user is None:
        return

    stats = StatsRepository(session)
    sub_repo = SubscriptionRepository(session)

    await stats.track("start", user_id=user.id)

    sub_count = await sub_repo.count_by_user(user.id)
    has_subs = sub_count > 0

    name = escape_html(user.full_name or "birodar")
    admin_badge = " 👑" if is_admin else ""

    if has_subs:
        text = (
            f"Assalomu alaykum, <b>{name}</b>{admin_badge}!\n\n"
            f"Siz <b>{sub_count}</b> ta hududga obunasiz. "
            "Quyidagilardan birini tanlang:"
        )
        await message.answer(
            text, reply_markup=main_menu_keyboard(has_subscriptions=True)
        )
    else:
        text = (
            f"Assalomu alaykum, <b>{name}</b>{admin_badge}!\n\n"
            "🕌 <b>@nmsupportbot</b> — Namoz vaqtlari, eslatmalar va taqvim rasmiy boti.\n\n"
            "Boshlash uchun hududingizni qanday topamiz?"
        )
        await message.answer(text, reply_markup=onboarding_keyboard())

    logger.info("/start: user_id={} tg_id={} subs={}", user.id, user.tg_id, sub_count)
