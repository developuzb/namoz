"""Matplotlib bilan admin uchun PNG grafiklarni yasaydi."""
from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta

import matplotlib

matplotlib.use("Agg")  # backend, GUI yo'q
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.db.models.post_log import PostLog
from app.db.models.stats import StatEvent
from app.db.models.user import User

# Brand ranglar
COLOR_PRIMARY = "#0c4628"   # to'q yashil
COLOR_GOLD = "#d4a85f"
COLOR_ERROR = "#dc2626"
COLOR_TEXT = "#1f2937"
COLOR_GRID = "#e5e7eb"


def _setup_axes(ax) -> None:
    """Umumiy stil — toza, minimal."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLOR_GRID)
    ax.spines["bottom"].set_color(COLOR_GRID)
    ax.tick_params(colors=COLOR_TEXT, labelsize=10)
    ax.grid(True, axis="y", linestyle="--", alpha=0.4, color=COLOR_GRID)


async def render_growth_chart(session: AsyncSession, days: int = 30) -> bytes:
    """User va event growth oxirgi `days` kun uchun.

    Returns:
        PNG bayt-massiv (Telegram BufferedInputFile uchun).
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Per-day yangi user soni
    user_rows = (await session.execute(
        select(
            func.date(User.created_at).label("d"),
            func.count().label("c"),
        )
        .where(User.created_at >= cutoff)
        .group_by("d")
        .order_by("d")
    )).all()
    user_dates = [datetime.fromisoformat(str(r.d)).date() for r in user_rows]
    user_counts = [r.c for r in user_rows]

    # Per-day total events
    ev_rows = (await session.execute(
        select(
            func.date(StatEvent.created_at).label("d"),
            func.count().label("c"),
        )
        .where(StatEvent.created_at >= cutoff)
        .group_by("d")
        .order_by("d")
    )).all()
    ev_dates = [datetime.fromisoformat(str(r.d)).date() for r in ev_rows]
    ev_counts = [r.c for r in ev_rows]

    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    _setup_axes(ax)

    if user_dates:
        ax.plot(
            user_dates, user_counts,
            color=COLOR_PRIMARY, linewidth=2.5,
            marker="o", markersize=6, label="Yangi userlar",
        )
    if ev_dates:
        ax.plot(
            ev_dates, ev_counts,
            color=COLOR_GOLD, linewidth=2.5, linestyle="--",
            marker="s", markersize=5, label="Eventlar",
        )

    ax.set_title(
        f"O'sish — so'nggi {days} kun",
        color=COLOR_TEXT, fontsize=14, fontweight="bold", pad=15,
    )
    ax.legend(loc="upper left", framealpha=0.9, frameon=True)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=10))
    fig.autofmt_xdate(rotation=30, ha="right")

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor="white", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    logger.debug("Growth chart yasaldi ({} kun)", days)
    return buf.getvalue()


async def render_post_status_chart(
    session: AsyncSession, hours: int = 24
) -> bytes:
    """Post_logs status taqsimoti oxirgi N soat (bar chart)."""
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    rows = (await session.execute(
        select(PostLog.status, func.count())
        .where(PostLog.posted_at >= cutoff)
        .group_by(PostLog.status)
    )).all()

    statuses = {r[0]: r[1] for r in rows}
    labels = ["ok", "error", "blocked"]
    counts = [statuses.get(s, 0) for s in labels]
    colors = [COLOR_PRIMARY, COLOR_ERROR, "#9ca3af"]

    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    _setup_axes(ax)

    bars = ax.bar(labels, counts, color=colors, width=0.6)
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2, h + max(counts) * 0.02,
                str(int(h)),
                ha="center", va="bottom",
                color=COLOR_TEXT, fontsize=12, fontweight="bold",
            )

    ax.set_title(
        f"Postlar holati — oxirgi {hours} soat",
        color=COLOR_TEXT, fontsize=14, fontweight="bold", pad=15,
    )
    ax.set_ylabel("Soni", color=COLOR_TEXT, fontsize=11)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor="white", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    logger.debug("Post status chart yasaldi ({} h)", hours)
    return buf.getvalue()


__all__ = ["render_growth_chart", "render_post_status_chart"]
