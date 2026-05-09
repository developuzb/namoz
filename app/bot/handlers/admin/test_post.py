"""/test_post — admin uchun: kunlik post pipeline'ini darhol triggers qiladi.

Bu — scheduler 06:00 da ishlatadigan `run_daily_post` ning aynan o'zi.
Test va debug uchun foydali (06:00 ni kutmaslik uchun).
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.filters import AdminFilter
from app.bot.keyboards.callback_data import CB_ADMIN_TEST_POST
from app.core.logger import logger
from app.db.models.user import User
from app.scheduler.jobs.daily_post import run_daily_post

router = Router(name="admin.test_post")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.message(Command("test_post"))
async def cmd_test_post(message: Message, user: User) -> None:
    await _run(message, user)


@router.callback_query(F.data == CB_ADMIN_TEST_POST)
async def cb_test_post(call: CallbackQuery, user: User) -> None:
    await call.answer("⏳ Test post boshlandi...")
    await _run(call.message, user)


async def _run(message: Message, user: User) -> None:
    """Kunlik post pipeline'ini ishga tushiradi va admin'ga statistika beradi."""
    notice = await message.answer(
        "⏳ <b>Test post boshlandi</b>\n\n"
        "Kanal va DM obunachilarga 06:00'dagi pipeline'ning aynan o'zi yuboriladi.\n"
        "Loglarda batafsil natija."
    )

    logger.info("/test_post: tg_id={} tomonidan triggers qilindi", user.tg_id)

    try:
        await run_daily_post(message.bot)
    except Exception as e:
        logger.exception("test_post fail: {}", e)
        await message.answer(f"❌ Xato: <code>{type(e).__name__}: {e}</code>")
        return

    await message.answer(
        "✅ <b>Test post tugadi</b>\n\n"
        "Kanal va DM obunachilarga vaqtlar yuborildi. "
        "Statistika uchun loglarni ko'ring."
    )
    # Avvalgi "boshlandi" xabarni o'chirib qo'yamiz (chuqurlik kamayadi)
    try:
        await notice.delete()
    except Exception:
        pass
