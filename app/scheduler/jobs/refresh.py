"""Har kuni farz va tahajjud notification job'larni qayta yaratish.

Vaqtlar har kuni o'zgaradi, shu sababli har 24 soatda eski job'lar tozalanib,
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
from app.db.repositories.masjid_time_repo import MasjidTimeRepository
from app.db.repositories.region_repo import RegionRepository
from app.db.session import get_session
from app.scheduler.jobs.farz_notification import fire_farz_notification
from app.scheduler.jobs.tahajjud_notification import fire_tahajjud_notification
from app.services.registry import get_prayer_service
from app.services.time_calculator import calculate_nafl_windows

#: Job ID prefiksi (refresh paytida shu prefiksli job'lar o'chiriladi)
_FARZ_PREFIX = "farz_"
_TAHAJJUD_PREFIX = "tahajjud_"


async def refresh_farz_jobs(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    """notify_farz va notify_nafl flag'lari bo'yicha bugungi job'larni qayta yaratish."""
    settings = get_settings()
    today = date.today()

    # 1. Eski farz va tahajjud job'larni o'chirish
    removed = 0
    for job in list(scheduler.get_jobs()):
        if job.id and (
            job.id.startswith(_FARZ_PREFIX) or job.id.startswith(_TAHAJJUD_PREFIX)
        ):
            scheduler.remove_job(job.id)
            removed += 1
    if removed:
        logger.info("Eski farz/tahajjud job'lari o'chirildi: {}", removed)

    prayer_service = get_prayer_service()
    farz_added = 0
    tahajjud_added = 0
    skipped_no_subs = 0
    skipped_no_times = 0

    async with get_session() as session:
        # notify_farz=True bo'lgan region'lar
        farz_result = await session.execute(
            select(Subscription.region_id)
            .distinct()
            .where(Subscription.notify_farz.is_(True))
        )
        farz_region_ids = {r[0] for r in farz_result}

        # notify_nafl=True bo'lgan region'lar (tahajjud uchun)
        nafl_result = await session.execute(
            select(Subscription.region_id)
            .distinct()
            .where(Subscription.notify_nafl.is_(True))
        )
        tahajjud_region_ids = {r[0] for r in nafl_result}

        all_region_ids = farz_region_ids | tahajjud_region_ids

        if not all_region_ids:
            logger.info("Refresh: notify_farz va notify_nafl obunachi yo'q")
            return

        rr = RegionRepository(session)
        mr = MasjidTimeRepository(session)

        for region_id in all_region_ids:
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
                    "Region '{}' timezone noto'g'ri ({!r}) — {} ishlatiladi. "
                    "Admin panelda tuzating, aks holda eslatmalar noto'g'ri "
                    "vaqtda ketishi mumkin!",
                    region.name, tz_name, settings.TIMEZONE,
                )
                tz = pytz.timezone(settings.TIMEZONE)

            now = datetime.now(tz)

            # ===== Farz job'lari =====
            if region_id in farz_region_ids:
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
                        continue

                    job_id = f"{_FARZ_PREFIX}{region.id}_{prayer}_{today.isoformat()}"
                    scheduler.add_job(
                        fire_farz_notification,
                        trigger=DateTrigger(run_date=fire_dt),
                        args=[bot, region.id, prayer, t],
                        id=job_id,
                        replace_existing=True,
                        misfire_grace_time=120,
                    )
                    farz_added += 1

            # ===== Tahajjud job =====
            if region_id in tahajjud_region_ids:
                masjid = await mr.get_for_region(region_id)
                nafl_windows = calculate_nafl_windows(
                    region_times=pt.times,
                    masjid_times=masjid,
                    target_date=today,
                    tz=tz,
                )
                tahajjud_window = nafl_windows.get("Tahajjud")
                if tahajjud_window:
                    # "01:48 — 03:58" → start = "01:48"
                    start_str = tahajjud_window.split("—")[0].strip()
                    try:
                        hh, mm = map(int, start_str.split(":"))
                    except (ValueError, AttributeError):
                        continue

                    fire_dt = tz.localize(
                        datetime(today.year, today.month, today.day, hh, mm)
                    )
                    # Tahajjud yarim tunda boshlanadi — agar bugungi shaklida vaqt
                    # allaqachon o'tgan bo'lsa, ehtimol u kechagi tahajjud edi.
                    # Ertangi tahajjud bugungi 23:xx atrofida bo'lishi mumkin emas
                    # (chunki u Bomdod oldidan, ya'ni ertaning birinchi soatlarida).
                    if fire_dt <= now:
                        continue

                    job_id = f"{_TAHAJJUD_PREFIX}{region.id}_{today.isoformat()}"
                    scheduler.add_job(
                        fire_tahajjud_notification,
                        trigger=DateTrigger(run_date=fire_dt),
                        args=[bot, region.id, start_str],
                        id=job_id,
                        replace_existing=True,
                        misfire_grace_time=120,
                    )
                    tahajjud_added += 1

    logger.info(
        "🔄 Refresh: {} farz + {} tahajjud job (skipped: no_subs={}, no_times={})",
        farz_added, tahajjud_added, skipped_no_subs, skipped_no_times,
    )


__all__ = ["refresh_farz_jobs"]
