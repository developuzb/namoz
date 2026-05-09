"""User handlerlari — barcha foydalanuvchilar uchun."""
from aiogram import Router

from app.bot.handlers.user.info import router as info_router
from app.bot.handlers.user.location import router as location_router
from app.bot.handlers.user.menu import router as menu_router
from app.bot.handlers.user.regions import router as regions_router
from app.bot.handlers.user.settings import router as settings_router
from app.bot.handlers.user.start import router as start_router

router = Router(name="user")
router.include_router(start_router)
router.include_router(menu_router)
router.include_router(location_router)
router.include_router(regions_router)
router.include_router(info_router)
router.include_router(settings_router)

__all__ = ["router"]
