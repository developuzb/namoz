"""Admin paneli — /admin entrypoint."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.filters import AdminFilter
from app.bot.keyboards import admin_panel_keyboard
from app.core.logger import logger
from app.db.models.user import User

router = Router(name="admin.panel")
# Bu router ichidagi BARCHA message handler lar admin filter dan o'tadi
router.message.filter(AdminFilter())


@router.message(Command("admin"))
async def cmd_admin(message: Message, user: User) -> None:
    text = (
        "👑 <b>Admin paneli</b>\n\n"
        "Quyidagilardan birini tanlang:"
    )
    await message.answer(text, reply_markup=admin_panel_keyboard())
    logger.info("/admin: tg_id={}", user.tg_id)
