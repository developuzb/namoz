"""Har kuni farz notification job'larni qayta yaratish.

Vaqtlar har kuni o'zgaradi, shu sababli har 24 soatda eski farz job'lar tozalanib,
bugungi vaqtlar uchun yangi DateTrigger'lar qo'yiladi.
"""
from __future__ import annotations

from datetime import date, datetime

import pytz
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from sqlalchemy import select

from app.core.config import get_settings
from app.core.constants import FARZ_PRAYERS
from app.core.exceptions import ProviderError
from app.core.logger import logger
from app.db.models.subscription import Subscription
from app.db.repositories.region_repo import RegionRepository
from app.db.session import get_session
from app.scheduler.jobs.farz_notification import fire_farz_notification
from app.services.registry import get_prayer_service

#: Job ID prefiksi (refresh paytida shu prefiksli job'lar o'chiriladi)
_FARZ_PREFIX = "farz_"


async def refresh_farz_jobs(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    """notify_farz=True ga ega regionlar uchun farz job'larni qayta yaratish."""
    settings = get_settings()
    today = date.today()

    # 1. Eski farz job'larni o'chirish
    removed = 0
    for job in list(scheduler.get_jobs()):
        if job.id and job.id.startswith(_FARZ_PREFIX):
            scheduler.remove_job(job.id)
            removed += 1
    if removed:
        logger.info("Eski farz job'lari o'chirildi: {}", removed)

    prayer_service = get_prayer_service()
    added = 0
    skipped_no_subs = 0
    skipped_no_times = 0

    async with get_session() as session:
        # notify_farz=True bo'lgan obunalardagi region_id'lar
        result = await session.execute(
            select(Subscription.region_id)
            .distinct()
            .where(Subscription.notify_farz.is_(True))
        )
        region_ids = [r[0] for r in result]

        if not region_ids:
            logger.info("Refresh: notify_farz=True obunachi yo'q")
            return

        rr = RegionRepository(session)

        for region_id in region_ids:
            region = await rr.get(region_id)
            if region is None or not region.is_active:
                skipped_no_subs += 1
                continue

            try:
                pt = await prayer_service.fetch_for_region(region, today)
            except ProviderError as e:
                logger.warning(
                    "Refresh: {} uchun vaqt olinmadi: {}", region.name, e,
                )
                skipped_no_times += 1
                continue

            tz_name = region.timezone or settings.TIMEZONE
            try:
                tz = pytz.timezone(tz_name)
            except pytz.UnknownTimeZoneError:
                logger.warning(
                    "Refresh: {} noma'lum tz={}", region.name, tz_name,
                )
                tz = pytz.timezone(settings.TIMEZONE)

            now = datetime.now(tz)

            for prayer in FARZ_PRAYERS:
                t = pt.get(prayer)
                if not t:
                    continue

                try:
                    hh, mm = map(int, t.split(":"))
                except (ValueError, AttributeError):
                    continue

                fire_dt = tz.localize(
                    datetime(today.year, today.month, today.day, hh, mm)
                )
                if fire_dt <= now:
                    continue  # vaqt allaqachon o'tgan

                job_id = f"{_FARZ_PREFIX}{region.id}_{prayer}_{today.isoformat()}"
                scheduler.add_job(
                    fire_farz_notification,
                    trigger=DateTrigger(run_date=fire_dt),
                    args=[bot, region.id, prayer, t],
                    id=job_id,
                    replace_existing=True,
                    misfire_grace_time=120,
                )
                added += 1

    logger.info(
        "🔄 Refresh: {} ta yangi farz job (skipped: no_subs={}, no_times={})",
        added, skipped_no_subs, skipped_no_times,
    )


__all__ = ["refresh_farz_jobs"]
