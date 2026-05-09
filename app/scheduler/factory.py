"""APScheduler yasovchi."""
from __future__ import annotations

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings
from app.core.logger import logger


def create_scheduler() -> AsyncIOScheduler:
    """Default timezone bo'yicha AsyncIOScheduler."""
    settings = get_settings()
    tz = pytz.timezone(settings.TIMEZONE)
    scheduler = AsyncIOScheduler(timezone=tz)
    logger.debug("Scheduler yaratildi (tz={})", settings.TIMEZONE)
    return scheduler


__all__ = ["create_scheduler"]
