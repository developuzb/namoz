"""Subscription repository — User ↔ Region."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.db.models.subscription import Subscription
from app.db.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription]):
    model = Subscription

    async def get_one(self, user_id: int, region_id: int) -> Subscription | None:
        return await self.get_by(user_id=user_id, region_id=region_id)

    async def list_by_user(self, user_id: int) -> list[Subscription]:
        stmt = (
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .options(joinedload(Subscription.region))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_region(
        self,
        region_id: int,
        *,
        notify_farz: bool | None = None,
        daily_post: bool | None = None,
    ) -> list[Subscription]:
        """Hudud uchun obuna bo'lgan userlar."""
        stmt = (
            select(Subscription)
            .where(Subscription.region_id == region_id)
            .options(joinedload(Subscription.user))
        )
        if notify_farz is not None:
            stmt = stmt.where(Subscription.notify_farz.is_(notify_farz))
        if daily_post is not None:
            stmt = stmt.where(Subscription.daily_post.is_(daily_post))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_user(self, user_id: int) -> int:
        return await self.count(user_id=user_id)

    async def toggle_subscription(
        self, user_id: int, region_id: int
    ) -> tuple[Subscription | None, bool]:
        """Obuna bo'lgan bo'lsa o'chiradi, bo'lmasa yaratadi.

        Returns (subscription_or_None, was_created).
        """
        existing = await self.get_one(user_id, region_id)
        if existing is not None:
            await self.delete(existing)
            return None, False

        sub = await self.create(user_id=user_id, region_id=region_id)
        return sub, True
