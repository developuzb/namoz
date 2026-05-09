"""Scheduler — APScheduler bilan kunlik post va farz eslatmalar."""
from __future__ import annotations

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.core.logger import logger
from app.scheduler.factory import create_scheduler
from app.scheduler.jobs import (
    fire_farz_notification,
    refresh_farz_jobs,
    run_daily_post,
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

    logger.info(
        "📅 Scheduler ulandi: daily_post @ {:02d}:{:02d}, refresh_farz @ 00:05",
        settings.post_hour, settings.post_minute,
    )


async def bootstrap_jobs(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    """Bot start bo'lganida darhol bir marta refresh — bugungi farz job'larni qo'yish."""
    try:
        await refresh_farz_jobs(scheduler, bot)
    except Exception as e:
        logger.exception("Bootstrap refresh xato: {}", e)


__all__ = [
    "bootstrap_jobs",
    "create_scheduler",
    "fire_farz_notification",
    "refresh_farz_jobs",
    "register_scheduler",
    "run_daily_post",
]
