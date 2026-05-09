"""Bot entrypoint: `python -m app` yoki `uv run python -m app`."""
from __future__ import annotations

import asyncio

from aiogram.types import ErrorEvent

from app.bot import create_bot, create_dispatcher, register_routers
from app.bot.middlewares import DBSessionMiddleware, UserRegisterMiddleware
from app.core import logger, setup_logger
from app.db.session import close_engine
from app.scheduler import bootstrap_jobs, create_scheduler, register_scheduler


async def main() -> None:
    setup_logger()
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
    # Boshlash bilan birga bugungi farz job'larni qo'yamiz
    await bootstrap_jobs(scheduler, bot)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        await close_engine()
        logger.info("👋 Bot to'xtatildi")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("⛔ Foydalanuvchi to'xtatdi")
