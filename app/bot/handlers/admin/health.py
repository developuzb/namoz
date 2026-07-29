"""Admin: `/health` — provider va tizim holatini tekshirish."""
from __future__ import annotations

import asyncio
from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters import AdminFilter
from app.core.exceptions import ProviderError
from app.core.logger import logger
from app.db.models.region import Region
from app.services.prayer_provider import (
    AladhanProvider,
    GeoPoint,
    IslomapiProvider,
    PraytimeProvider,
)

router = Router(name="admin.health")
router.message.filter(AdminFilter())


async def _check_islomapi() -> tuple[bool, str]:
    try:
        pt = await IslomapiProvider().fetch("Qarshi", date.today())
        return True, f"OK ({len(pt.times)} vaqt)"
    except ProviderError as e:
        return False, f"FAIL: {e}"


async def _check_praytime() -> tuple[bool, str]:
    try:
        pt = await PraytimeProvider().fetch(121, date.today())
        return True, f"OK ({len(pt.times)} vaqt)"
    except ProviderError as e:
        return False, f"FAIL: {e}"


async def _check_aladhan() -> tuple[bool, str]:
    try:
        pt = await AladhanProvider().fetch(GeoPoint(41.31, 69.24), date.today())
        return True, f"OK ({len(pt.times)} vaqt, tz={pt.timezone})"
    except ProviderError as e:
        return False, f"FAIL: {e}"


async def _check_db(session: AsyncSession) -> tuple[bool, str]:
    try:
        count = await session.scalar(
            select(func.count()).select_from(Region)
        )
        return True, f"OK ({count} ta region)"
    except Exception as e:  # noqa: BLE001
        logger.warning("Health DB tekshiruvi xato: {}", e)
        return False, f"FAIL: {e}"


@router.message(Command("health"))
async def cmd_health(message: Message, session: AsyncSession) -> None:
    notice = await message.answer("⏳ Tekshirilmoqda...")

    isl_task = asyncio.create_task(_check_islomapi())
    pry_task = asyncio.create_task(_check_praytime())
    ala_task = asyncio.create_task(_check_aladhan())
    db_task = asyncio.create_task(_check_db(session))

    results = await asyncio.gather(isl_task, pry_task, ala_task, db_task)
    isl, pry, ala, db = results

    def line(name: str, status: tuple[bool, str]) -> str:
        ok, msg = status
        icon = "🟢" if ok else "🔴"
        return f"{icon} <b>{name}</b>: <code>{msg}</code>"

    text = (
        "🩺 <b>Tizim sog'ligi</b>\n\n"
        f"{line('islomapi.uz', isl)}\n"
        f"{line('praytime.uz', pry)}\n"
        f"{line('aladhan.com', ala)}\n"
        f"{line('Database', db)}\n\n"
        "<i>Provider chain: islomapi → praytime → aladhan</i>"
    )

    try:
        await notice.delete()
    except Exception:  # noqa: BLE001
        pass
    await message.answer(text)
