"""Scheduler — APScheduler bilan kunlik post va farz eslatmalar."""
from __future__ import annotations

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import get_settings
from app.core.logger import logger
from app.scheduler.factory import create_scheduler
from app.scheduler.jobs import (
    fire_farz_notification,
    refresh_farz_jobs,
    restore_from_sheets,
    run_daily_post,
    run_db_backup,
    run_qashqadaryo_post,
    run_sheets_sync,
)


def register_scheduler(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    """Cron job'larni qo'shadi:

    - **Kunlik post** (06:00 default) — kanal + DM ga rasm + caption
    - **Refresh** (00:05) — farz job'larni shu kungi vaqtlar uchun qaytadan rejalashtirish

    Farz notification job'lari refresh tomonidan dinamik qo'shiladi.
    """
    settings = get_settings()

    # 1. Kunlik post — har kuni DAILY_POST_TIME da
    scheduler.add_job(
        run_daily_post,
        trigger=CronTrigger(
            hour=settings.post_hour,
            minute=settings.post_minute,
            timezone=settings.TIMEZONE,
        ),
        args=[bot],
        id="daily_post",
        replace_existing=True,
        misfire_grace_time=300,  # 5 daqiqa kechiksa ham bajaradi
    )

    # 2. Refresh — har kuni 00:05 da farz job'larni qaytadan tuzish
    scheduler.add_job(
        refresh_farz_jobs,
        trigger=CronTrigger(hour=0, minute=5, timezone=settings.TIMEZONE),
        args=[scheduler, bot],
        id="refresh_farz",
        replace_existing=True,
        misfire_grace_time=600,
    )

    # 3. DB backup — har kuni 03:00 da
    scheduler.add_job(
        run_db_backup,
        trigger=CronTrigger(hour=3, minute=0, timezone=settings.TIMEZONE),
        id="db_backup",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # 4. Google Sheets sync — service account kaliti mavjud bo'lsagina
    if settings.sheets_configured:
        scheduler.add_job(
            run_sheets_sync,
            trigger=IntervalTrigger(
                minutes=settings.SHEETS_SYNC_INTERVAL_MIN,
                timezone=settings.TIMEZONE,
            ),
            id="sheets_sync",
            replace_existing=True,
            misfire_grace_time=600,
        )
        logger.info(
            "📊 Sheets sync yoqildi: har {} daqiqada",
            settings.SHEETS_SYNC_INTERVAL_MIN,
        )

    # 5. Qashqadaryo kunlik plakat — NAMOZ_CHAT_ID o'rnatilgan bo'lsagina
    if settings.namoz_chat_id:
        scheduler.add_job(
            run_qashqadaryo_post,
            trigger=CronTrigger(
                hour=settings.namoz_hour,
                minute=settings.namoz_minute,
                timezone=settings.NAMOZ_TIMEZONE,
            ),
            args=[bot],
            id="qashqadaryo_post",
            replace_existing=True,
            misfire_grace_time=600,
        )
        logger.info(
            "📅 Scheduler: daily_post @ {:02d}:{:02d}, refresh @ 00:05, "
            "db_backup @ 03:00, qashqadaryo @ {:02d}:{:02d} → chat {}",
            settings.post_hour, settings.post_minute,
            settings.namoz_hour, settings.namoz_minute, settings.namoz_chat_id,
        )
    else:
        logger.info(
            "📅 Scheduler: daily_post @ {:02d}:{:02d}, refresh @ 00:05, "
            "db_backup @ 03:00 (NAMOZ_CHAT_ID=0 — Qashqadaryo post o'chiq)",
            settings.post_hour, settings.post_minute,
        )


async def bootstrap_jobs(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    """Bot start bo'lganida bir martalik ishlar.

    1. DB bo'sh bo'lsa — Google Sheets'dan tiklash (dyno/server restart holati)
    2. Bugungi farz job'larni qo'yish
    3. Ilk Sheets sync (fonda)
    """
    try:
        if await restore_from_sheets():
            logger.info("♻️ Bootstrap: ma'lumotlar Sheets'dan tiklandi")
    except Exception as e:
        logger.exception("Bootstrap Sheets restore xato: {}", e)

    try:
        await refresh_farz_jobs(scheduler, bot)
    except Exception as e:
        logger.exception("Bootstrap refresh xato: {}", e)

    if get_settings().sheets_configured:
        # run_sheets_sync barcha xatolarni ichida ushlaydi — fonda xavfsiz
        import asyncio

        asyncio.create_task(run_sheets_sync())  # noqa: RUF006


__all__ = [
    "bootstrap_jobs",
    "create_scheduler",
    "fire_farz_notification",
    "refresh_farz_jobs",
    "register_scheduler",
    "run_daily_post",
    "run_db_backup",
    "run_qashqadaryo_post",
]
