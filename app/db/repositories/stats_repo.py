"""Stats repository — event log."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from app.db.models.stats import StatEvent
from app.db.repositories.base import BaseRepository


class StatsRepository(BaseRepository[StatEvent]):
    model = StatEvent

    async def track(
        self,
        event: str,
        *,
        user_id: int | None = None,
        region_id: int | None = None,
        meta: dict[str, Any] | None = None,
    ) -> StatEvent:
        """Yangi event qo'shish (shortcut)."""
        return await self.create(
            event=event,
            user_id=user_id,
            region_id=region_id,
            meta=meta,
        )

    async def count_event(self, event: str, *, since: datetime | None = None) -> int:
        stmt = select(func.count()).select_from(StatEvent).where(StatEvent.event == event)
        if since:
            stmt = stmt.where(StatEvent.created_at >= since)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def event_counts(self, *, days: int = 7) -> dict[str, int]:
        """Oxirgi N kundagi har event bo'yicha sanash."""
        since = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(StatEvent.event, func.count())
            .where(StatEvent.created_at >= since)
            .group_by(StatEvent.event)
        )
        result = await self.session.execute(stmt)
        return {event: count for event, count in result.all()}

    async def daily_active_users(self, *, days: int = 7) -> int:
        """Oxirgi N kunda eventi bo'lgan unique user lar soni."""
        since = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(func.count(func.distinct(StatEvent.user_id)))
            .where(StatEvent.created_at >= since, StatEvent.user_id.is_not(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
