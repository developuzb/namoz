"""Admin: audit log viewer — so'nggi post_logs va stat_events."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters import AdminFilter
from app.db.models.post_log import PostLog
from app.db.models.stats import StatEvent
from app.utils.text_utils import escape_html, truncate

router = Router(name="admin.audit")
router.message.filter(AdminFilter())


@router.message(Command("audit"))
async def cmd_audit(message: Message, session: AsyncSession) -> None:
    """So'nggi post_logs (xato + ok) va eventlar."""
    # 1. So'nggi 10 ta post_log
    log_stmt = (
        select(PostLog).order_by(desc(PostLog.posted_at)).limit(10)
    )
    log_rows = list((await session.execute(log_stmt)).scalars().all())

    # 2. So'nggi 10 ta stat_event
    ev_stmt = (
        select(StatEvent).order_by(desc(StatEvent.created_at)).limit(10)
    )
    ev_rows = list((await session.execute(ev_stmt)).scalars().all())

    # Format
    log_lines = []
    for log in log_rows:
        icon = {"ok": "✅", "error": "❌", "blocked": "🚫"}.get(log.status, "•")
        err = f" — {truncate(log.error or '', 40)}" if log.error else ""
        log_lines.append(
            f"{icon} <code>{log.post_type}</code> chat={log.chat_id} "
            f"<i>{log.posted_at:%H:%M:%S}</i>{escape_html(err)}"
        )

    ev_lines = []
    for ev in ev_rows:
        ev_lines.append(
            f"• <code>{ev.event}</code> "
            f"user_id={ev.user_id or '—'} "
            f"region_id={ev.region_id or '—'} "
            f"<i>{ev.created_at:%H:%M:%S}</i>"
        )

    text = (
        "📋 <b>Audit log</b>\n\n"
        "<b>So'nggi 10 post:</b>\n"
        + ("\n".join(log_lines) if log_lines else "<i>Bo'sh</i>")
        + "\n\n<b>So'nggi 10 event:</b>\n"
        + ("\n".join(ev_lines) if ev_lines else "<i>Bo'sh</i>")
    )

    # Telegram message limit ~4096
    if len(text) > 4000:
        text = text[:3990] + "...</i>"

    await message.answer(text)
