"""Channel repository."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.db.models.channel import Channel
from app.db.repositories.base import BaseRepository


class ChannelRepository(BaseRepository[Channel]):
    model = Channel

    async def get_by_chat_id(self, chat_id: int) -> Channel | None:
        return await self.get_by(chat_id=chat_id)

    async def list_by_region(self, region_id: int, *, only_active: bool = True) -> list[Channel]:
        stmt = select(Channel).where(Channel.region_id == region_id)
        if only_active:
            stmt = stmt.where(Channel.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_active_with_region(self) -> list[Channel]:
        """Barcha aktiv kanallarni hudud bilan (kunlik post uchun)."""
        stmt = (
            select(Channel)
            .where(Channel.is_active.is_(True))
            .options(joinedload(Channel.region))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
