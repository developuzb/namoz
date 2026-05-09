"""Admin statistika dashboard — `/stats` va admin paneldagi 📊 tugmasi."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters import AdminFilter
from app.bot.keyboards.callback_data import CB_ADMIN_STATS
from app.db.models.channel import Channel
from app.db.models.subscription import Subscription
from app.db.models.user import User
from app.db.repositories.post_log_repo import PostLogRepository
from app.db.repositories.stats_repo import StatsRepository

router = Router(name="admin.stats")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

#: Event nomlari ko'rsatilish tartibi
_EVENT_ORDER = (
    "start",
    "subscribe",
    "unsubscribe",
    "click_next_farz",
    "click_nafl_info",
    "settings_changed",
)


async def _gather_stats(session: AsyncSession) -> dict:
    """Asosiy ko'rsatkichlarni yig'adi."""
    now = datetime.now(UTC)
    last_24h = now - timedelta(hours=24)

    # Foydalanuvchilar
    users_total = await session.scalar(select(func.count()).select_from(User)) or 0
    users_blocked = (
        await session.scalar(
            select(func.count()).select_from(User).where(User.is_blocked.is_(True))
        )
        or 0
    )

    # Obunalar
    subs_total = (
        await session.scalar(select(func.count()).select_from(Subscription)) or 0
    )

    # Aktiv kanallar
    channels_active = (
        await session.scalar(
            select(func.count()).select_from(Channel).where(Channel.is_active.is_(True))
        )
        or 0
    )

    # Postlar (24 soat)
    log_repo = PostLogRepository(session)
    posts_ok = await log_repo.count_by_status(since=last_24h, status="ok")
    posts_err = await log_repo.count_by_status(since=last_24h, status="error")
    posts_blocked = await log_repo.count_by_status(since=last_24h, status="blocked")

    # Eventlar (7 kun)
    stats_repo = StatsRepository(session)
    events_7d = await stats_repo.event_counts(days=7)
    dau_7d = await stats_repo.daily_active_users(days=7)

    # So'nggi xatolar
    recent_errors = await log_repo.recent_errors(hours=24, limit=3)

    return {
        "users_total": users_total,
        "users_blocked": users_blocked,
        "users_active": users_total - users_blocked,
        "subs_total": subs_total,
        "channels_active": channels_active,
        "posts_24h_ok": posts_ok,
        "posts_24h_err": posts_err,
        "posts_24h_blocked": posts_blocked,
        "events_7d": events_7d,
        "dau_7d": dau_7d,
        "recent_errors": recent_errors,
    }


def _format_stats(s: dict) -> str:
    events = s["events_7d"]
    event_lines = [
        f"  • <code>{name}</code>: <b>{events.get(name, 0)}</b>"
        for name in _EVENT_ORDER
    ]

    err_section = ""
    if s["recent_errors"]:
        err_section = "\n\n<b>⚠️ So'nggi xatolar (24h)</b>\n"
        for err in s["recent_errors"]:
            short = (err.error or "")[:80].replace("\n", " ")
            err_section += (
                f"  • <code>{err.post_type}</code> chat={err.chat_id}: "
                f"{short}\n"
            )

    return (
        "📊 <b>Statistika</b>\n\n"
        "<b>👥 Foydalanuvchilar</b>\n"
        f"  • Jami: <b>{s['users_total']}</b>\n"
        f"  • Aktiv: <b>{s['users_active']}</b>\n"
        f"  • Bloklangan: <b>{s['users_blocked']}</b>\n"
        f"  • DAU (7 kun): <b>{s['dau_7d']}</b>\n\n"
        "<b>📍 Obunalar va kanallar</b>\n"
        f"  • Obunalar jami: <b>{s['subs_total']}</b>\n"
        f"  • Faol kanallar: <b>{s['channels_active']}</b>\n\n"
        "<b>📨 Postlar (24 soat)</b>\n"
        f"  • ✅ ok: <b>{s['posts_24h_ok']}</b>\n"
        f"  • ❌ error: <b>{s['posts_24h_err']}</b>\n"
        f"  • 🚫 blocked: <b>{s['posts_24h_blocked']}</b>\n\n"
        "<b>🎯 Eventlar (7 kun)</b>\n" + "\n".join(event_lines) + err_section
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession) -> None:
    s = await _gather_stats(session)
    await message.answer(_format_stats(s))


@router.callback_query(F.data == CB_ADMIN_STATS)
async def cb_stats(call: CallbackQuery, session: AsyncSession) -> None:
    s = await _gather_stats(session)
    await call.message.answer(_format_stats(s))
    await call.answer()
