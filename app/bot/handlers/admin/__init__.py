"""Admin handlerlari — faqat adminlar uchun (router darajasida AdminFilter)."""
from aiogram import Router

from app.bot.handlers.admin.broadcast import router as broadcast_router
from app.bot.handlers.admin.channels import router as channels_router
from app.bot.handlers.admin.health import router as health_router
from app.bot.handlers.admin.masjid_times import router as masjid_times_router
from app.bot.handlers.admin.panel import router as panel_router
from app.bot.handlers.admin.regions import router as regions_router
from app.bot.handlers.admin.stats import router as stats_router
from app.bot.handlers.admin.test_post import router as test_post_router

router = Router(name="admin")
router.include_router(panel_router)
router.include_router(stats_router)
router.include_router(test_post_router)
router.include_router(health_router)
router.include_router(channels_router)
router.include_router(regions_router)
router.include_router(masjid_times_router)
router.include_router(broadcast_router)

__all__ = ["router"]
