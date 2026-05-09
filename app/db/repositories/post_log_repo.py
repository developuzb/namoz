"""PostLog repository — yuborilgan postlar tarixi."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.db.models.post_log import PostLog
from app.db.repositories.base import BaseRepository


class PostLogRepository(BaseRepository[PostLog]):
    model = PostLog

    async def log(
        self,
        *,
        region_id: int | None,
        chat_id: int,
        post_type: str,
        status: str = "ok",
        message_id: int | None = None,
        error: str | None = None,
    ) -> PostLog:
        """Yangi yozuv qo'shish (qisqa shortcut)."""
        return await self.create(
            region_id=region_id,
            chat_id=chat_id,
            post_type=post_type,
            status=status,
            message_id=message_id,
            error=error,
        )

    async def count_by_status(
        self, *, since: datetime | None = None, status: str | None = None
    ) -> int:
        """Status bo'yicha sanash (statistika uchun)."""
        stmt = select(func.count()).select_from(PostLog)
        if status:
            stmt = stmt.where(PostLog.status == status)
        if since:
            stmt = stmt.where(PostLog.posted_at >= since)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def recent_errors(self, *, hours: int = 24, limit: int = 20) -> list[PostLog]:
        """Oxirgi N soatdagi xatolar."""
        since = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            select(PostLog)
            .where(PostLog.status == "error", PostLog.posted_at >= since)
            .order_by(PostLog.posted_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
