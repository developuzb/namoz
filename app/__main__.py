"""Bot entrypoint: `python -m app` yoki `uv run python -m app`."""
from __future__ import annotations

import asyncio

from aiogram.types import ErrorEvent

from app.bot import create_bot, create_dispatcher, register_routers
from app.bot.middlewares import DBSessionMiddleware, UserRegisterMiddleware
from app.core import logger, setup_logger
from app.core.config import get_settings
from app.db.session import close_engine
from app.scheduler import bootstrap_jobs, create_scheduler, register_scheduler
from app.web import create_web_app, run_web_server


async def main() -> None:
    setup_logger()
    settings = get_settings()
    logger.info("🚀 TAQVIMbot ishga tushyapti...")

    bot = create_bot()
    dp = create_dispatcher()

    # Middleware tartib MUHIM: avval session, keyin user register (sessiondan foydalanadi)
    dp.update.outer_middleware(DBSessionMiddleware())
    dp.update.outer_middleware(UserRegisterMiddleware())

    register_routers(dp)

    @dp.errors()
    async def on_error(event: ErrorEvent) -> bool:
        logger.opt(exception=event.exception).error(
            "Update da xato: {}", event.exception
        )
        return True

    me = await bot.get_me()
    logger.info("✅ Bot ulandi: @{} ({})", me.username, me.full_name)

    # Scheduler — kunlik post + farz notification
    scheduler = create_scheduler()
    register_scheduler(scheduler, bot)
    scheduler.start()
    await bootstrap_jobs(scheduler, bot)

    # Web server (Mini App backend) — port'da listen qiladi
    web_app = create_web_app()
    web_runner = await run_web_server(web_app, settings.WEBAPP_PORT)
    if settings.WEBAPP_URL:
        logger.info("🚀 Mini App: {}", settings.WEBAPP_URL)
    else:
        logger.info(
            "ℹ️  WEBAPP_URL bo'sh — Mini App tugmasi yashirilgan. "
            "Local'da: `ngrok http {}`", settings.WEBAPP_PORT,
        )

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown(wait=False)
        await web_runner.cleanup()
        await bot.session.close()
        await close_engine()
        logger.info("👋 Bot to'xtatildi")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("⛔ Foydalanuvchi to'xtatdi")
