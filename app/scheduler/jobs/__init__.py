"""Scheduler vazifalari."""
from app.scheduler.jobs.backup import run_db_backup
from app.scheduler.jobs.daily_post import run_daily_post
from app.scheduler.jobs.farz_notification import fire_farz_notification
from app.scheduler.jobs.qashqadaryo_post import (
    run_qashqadaryo_post,
    send_qashqadaryo_post,
)
from app.scheduler.jobs.refresh import refresh_farz_jobs
from app.scheduler.jobs.tahajjud_notification import fire_tahajjud_notification

__all__ = [
    "fire_farz_notification",
    "fire_tahajjud_notification",
    "refresh_farz_jobs",
    "run_daily_post",
    "run_db_backup",
    "run_qashqadaryo_post",
    "send_qashqadaryo_post",
]
