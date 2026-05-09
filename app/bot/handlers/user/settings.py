"""Sozlamalar — DM eslatma toggle handlerlari."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import settings_keyboard
from app.bot.keyboards.callback_data import (
    CB_SETTINGS,
    CB_TOGGLE_DAILY,
    CB_TOGGLE_FARZ,
    CB_TOGGLE_NAFL,
    CB_TOGGLE_QUIET,
)
from app.core.logger import logger
from app.db.models.user import User
from app.db.repositories.stats_repo import StatsRepository
from app.db.repositories.subscription_repo import SubscriptionRepository

router = Router(name="user.settings")


async def _render_settings(call: CallbackQuery, user: User, session: AsyncSession) -> None:
    sub_repo = SubscriptionRepository(session)
    user_subs = await sub_repo.list_by_user(user.id)

    if not user_subs:
        await call.answer(
            "Avval hudud tanlang — sozlamalar shu hududlar uchun ishlaydi",
            show_alert=True,
        )
        return

    notify_farz = any(s.notify_farz for s in user_subs)
    notify_nafl = any(s.notify_nafl for s in user_subs)
    daily_post = any(s.daily_post for s in user_subs)
    quiet_hours = bool(user.quiet_hours_enabled)

    text = (
        "⚙️ <b>Sozlamalar</b>\n\n"
        f"Sizning <b>{len(user_subs)}</b> ta obunangiz uchun amal qiladi.\n\n"
        "<i>🌙 Tinch soatlar — yoqilgan bo'lsa, kechqurun (23:00–05:00) "
        "farz va tahajjud eslatmalari yuborilmaydi.</i>"
    )

    await call.message.edit_text(
        text,
        reply_markup=settings_keyboard(
            notify_farz=notify_farz,
            notify_nafl=notify_nafl,
            daily_post=daily_post,
            quiet_hours=quiet_hours,
        ),
    )
    await call.answer()


@router.callback_query(F.data == CB_SETTINGS)
async def show_settings(
    call: CallbackQuery, user: User, session: AsyncSession
) -> None:
    await _render_settings(call, user, session)


async def _toggle_field(
    call: CallbackQuery,
    user: User,
    session: AsyncSession,
    field: str,
) -> None:
    sub_repo = SubscriptionRepository(session)
    stats = StatsRepository(session)

    user_subs = await sub_repo.list_by_user(user.id)
    if not user_subs:
        await call.answer("Obuna yo'q", show_alert=True)
        return

    # Agar kamida bittasi True bo'lsa False qil; aks holda hammasini True qil
    new_value = not any(getattr(s, field) for s in user_subs)
    for sub in user_subs:
        setattr(sub, field, new_value)
    await session.flush()

    await stats.track(
        "settings_changed",
        user_id=user.id,
        meta={"field": field, "value": new_value},
    )
    logger.info(
        "Settings: tg_id={} {}={}", user.tg_id, field, new_value
    )

    await _render_settings(call, user, session)


@router.callback_query(F.data == CB_TOGGLE_FARZ)
async def toggle_farz(
    call: CallbackQuery, user: User, session: AsyncSession
) -> None:
    await _toggle_field(call, user, session, "notify_farz")


@router.callback_query(F.data == CB_TOGGLE_NAFL)
async def toggle_nafl(
    call: CallbackQuery, user: User, session: AsyncSession
) -> None:
    await _toggle_field(call, user, session, "notify_nafl")


@router.callback_query(F.data == CB_TOGGLE_DAILY)
async def toggle_daily(
    call: CallbackQuery, user: User, session: AsyncSession
) -> None:
    await _toggle_field(call, user, session, "daily_post")


@router.callback_query(F.data == CB_TOGGLE_QUIET)
async def toggle_quiet_hours(
    call: CallbackQuery, user: User, session: AsyncSession
) -> None:
    """User darajasidagi quiet hours toggle (subscriptions emas, users)."""
    user.quiet_hours_enabled = not user.quiet_hours_enabled
    await session.flush()

    stats = StatsRepository(session)
    await stats.track(
        "settings_changed",
        user_id=user.id,
        meta={"field": "quiet_hours", "value": user.quiet_hours_enabled},
    )
    logger.info(
        "Settings: tg_id={} quiet_hours={}", user.tg_id, user.quiet_hours_enabled,
    )

    await call.answer(
        "🌙 Tinch soatlar yoqildi" if user.quiet_hours_enabled
        else "🔔 Tinch soatlar o'chirildi",
    )
    await _render_settings(call, user, session)
