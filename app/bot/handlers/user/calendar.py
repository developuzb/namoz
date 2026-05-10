"""/calendar — joriy oy uchun barcha kunlar prayer times rasmi."""
from __future__ import annotations

from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MONTHS_UZ
from app.core.logger import logger
from app.db.models.user import User
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.services.month_calendar import (
    get_month_data,
    make_month_calendar_image,
)
from app.utils.text_utils import escape_html

router = Router(name="user.calendar")


@router.message(Command("calendar"))
async def cmd_calendar(
    message: Message, user: User | None, session: AsyncSession
) -> None:
    if user is None:
        return

    sub_repo = SubscriptionRepository(session)
    subs = await sub_repo.list_by_user(user.id)
    if not subs:
        await message.answer("Avval hudud tanlang: /start")
        return

    region = subs[0].region
    today = date.today()
    year, month = today.year, today.month

    notice = await message.answer(
        f"⏳ <b>{MONTHS_UZ[month].capitalize()} {year}</b> kalendari "
        f"({region.name}) tayyorlanmoqda... Bu 5–30 sekund olishi mumkin."
    )

    try:
        days_data = await get_month_data(region, year, month)
    except Exception as e:  # noqa: BLE001
        logger.exception("Calendar month data fail: {}", e)
        await message.answer(f"❌ Xato: <code>{escape_html(str(e))}</code>")
        return

    if not days_data:
        await message.answer("⚠️ Hech qanday kun ma'lumoti olinmadi.")
        return

    img_path = make_month_calendar_image(
        region_name=region.name,
        year=year,
        month=month,
        days_data=days_data,
    )

    try:
        await notice.delete()
    except Exception:  # noqa: BLE001
        pass

    await message.answer_photo(
        photo=FSInputFile(img_path),
        caption=(
            f"📅 <b>{MONTHS_UZ[month].capitalize()} {year}</b> — "
            f"<i>{escape_html(region.name)}</i>\n\n"
            f"Jami {len(days_data)} kun ma'lumoti."
        ),
    )
    logger.info(
        "Calendar: tg_id={} region={} {} kun",
        user.tg_id, region.name, len(days_data),
    )
