"""Guruh chat obunalari repository."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.db.models.subscribed_chat import SubscribedChat
from app.db.repositories.base import BaseRepository


class SubscribedChatRepository(BaseRepository[SubscribedChat]):
    model = SubscribedChat

    async def get_by_chat_id(self, chat_id: int) -> SubscribedChat | None:
        return await self.get_by(chat_id=chat_id)

    async def list_active_with_region(self) -> list[SubscribedChat]:
        """Barcha aktiv guruh obunalarini hudud bilan eager-load."""
        stmt = (
            select(SubscribedChat)
            .where(SubscribedChat.is_active.is_(True))
            .options(joinedload(SubscribedChat.region))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
