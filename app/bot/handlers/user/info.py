"""Bugungi vaqtlar / Keyingi farz / Nafl info — info handlerlari."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytz
from aiogram import F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import CallbackQuery, FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.callback_data import (
    CB_MY_TIMES,
    CB_NAFL_NOW,
    CB_NEXT_FARZ,
    CB_TOMORROW_TIMES,
)
from app.core.config import get_settings
from app.core.constants import FARZ_PRAYERS
from app.core.exceptions import ProviderError
from app.core.logger import logger
from app.db.models.user import User
from app.db.repositories.stats_repo import StatsRepository
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.db.repositories.user_repo import UserRepository
from app.services.registry import get_post_service, get_prayer_service
from app.services.time_calculator import get_current_nafl_status
from app.utils.text_utils import escape_html
from app.utils.time_utils import format_eta, parse_hhmm_to_dt

router = Router(name="user.info")


async def _send_times_for_date(
    call: CallbackQuery,
    user: User,
    session: AsyncSession,
    target_date: date,
    *,
    label: str = "",
) -> None:
    """User'ning hamma obunalari uchun belgilangan kun vaqtlarini DM ga yuboradi."""
    sub_repo = SubscriptionRepository(session)
    user_subs = await sub_repo.list_by_user(user.id)

    if not user_subs:
        await call.answer("Avval hudud tanlang", show_alert=True)
        return

    notice = f"⏳ {label} vaqtlar tayyorlanmoqda..." if label else "⏳ Vaqtlar tayyorlanmoqda..."
    await call.answer(notice)

    for sub in user_subs:
        region = sub.region
        try:
            bundle = await get_post_service().build_for_region(
                session=session, region=region, target_date=target_date,
            )
            await call.bot.send_photo(
                chat_id=user.tg_id,
                photo=FSInputFile(bundle.image_path),
                caption=bundle.caption,
            )
        except ProviderError as e:
            logger.warning(
                "{} provider failed for {}: {}",
                label or "my_times", region.name, e,
            )
            await call.bot.send_message(
                chat_id=user.tg_id,
                text=(
                    f"⚠️ <b>{escape_html(region.name)}</b> uchun "
                    f"{label or 'bugungi'} vaqtlar olinmadi.\n"
                    "Keyinroq qayta urinib ko'ring."
                ),
            )
        except TelegramForbiddenError:
            logger.warning("User {} bloklagan", user.tg_id)
            user_repo = UserRepository(session)
            await user_repo.mark_blocked(user.tg_id)
            return


@router.callback_query(F.data == CB_MY_TIMES)
async def my_times(call: CallbackQuery, user: User, session: AsyncSession) -> None:
    await _send_times_for_date(call, user, session, date.today(), label="bugungi")


@router.callback_query(F.data == CB_TOMORROW_TIMES)
async def tomorrow_times(
    call: CallbackQuery, user: User, session: AsyncSession
) -> None:
    tomorrow = date.today() + timedelta(days=1)
    await _send_times_for_date(call, user, session, tomorrow, label="ertangi")


@router.callback_query(F.data == CB_NEXT_FARZ)
async def next_farz(call: CallbackQuery, user: User, session: AsyncSession) -> None:
    sub_repo = SubscriptionRepository(session)
    stats = StatsRepository(session)

    user_subs = await sub_repo.list_by_user(user.id)
    if not user_subs:
        await call.answer("Avval hudud tanlang", show_alert=True)
        return

    await stats.track("click_next_farz", user_id=user.id)

    settings = get_settings()
    tz = pytz.timezone(settings.TIMEZONE)
    today = date.today()
    now = datetime.now(tz)

    closest: tuple[str, str, datetime] | None = None  # (region_name, prayer, dt)

    for sub in user_subs:
        region = sub.region
        try:
            pt = await get_prayer_service().fetch_for_region(region, today)
        except ProviderError:
            continue

        for prayer in FARZ_PRAYERS:
            t = pt.get(prayer)
            if not t:
                continue
            dt = parse_hhmm_to_dt(t, today, tz)
            if dt and dt > now:
                if closest is None or dt < closest[2]:
                    closest = (region.name, prayer, dt)
                break  # bu region uchun keyingisiga qaramaymiz

    if closest is None:
        await call.answer(
            "Bugungi farz vaqtlari tugadi.\n"
            "Ertangi vaqtlar uchun ertaga 06:00 dan keyin /start",
            show_alert=True,
        )
        return

    region_name, prayer, dt = closest
    mins = int((dt - now).total_seconds() // 60)
    text = f"🕋 {region_name}\n{prayer}: {dt:%H:%M}\n\n⏳ {format_eta(mins)}"
    await call.answer(text, show_alert=True)


@router.callback_query(F.data == CB_NAFL_NOW)
async def nafl_now(call: CallbackQuery, user: User, session: AsyncSession) -> None:
    sub_repo = SubscriptionRepository(session)
    stats = StatsRepository(session)

    user_subs = await sub_repo.list_by_user(user.id)
    if not user_subs:
        await call.answer("Avval hudud tanlang", show_alert=True)
        return

    await stats.track("click_nafl_info", user_id=user.id)

    settings = get_settings()
    tz = pytz.timezone(settings.TIMEZONE)
    today = date.today()

    # Birinchi obuna bo'yicha (bir nechta bo'lsa, eng katta hudud odatda birinchi keladi)
    sub = user_subs[0]
    region = sub.region

    try:
        pt = await get_prayer_service().fetch_for_region(region, today)
    except ProviderError:
        await call.answer(
            f"⚠️ {region.name} uchun vaqtlar olinmadi", show_alert=True
        )
        return

    status = get_current_nafl_status(
        region_times=pt.times, target_date=today, tz=tz,
    )
    text = f"🌙 {region.name}\n\n{status}"
    await call.answer(text, show_alert=True)
