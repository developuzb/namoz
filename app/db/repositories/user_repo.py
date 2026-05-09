"""User repository."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models.user import User
from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_tg_id(self, tg_id: int) -> User | None:
        return await self.get_by(tg_id=tg_id)

    async def get_or_create(
        self,
        tg_id: int,
        *,
        username: str | None = None,
        full_name: str | None = None,
        language: str = "uz",
    ) -> tuple[User, bool]:
        """Mavjud bo'lsa qaytaradi, bo'lmasa yaratadi. Returns (user, created)."""
        user = await self.get_by_tg_id(tg_id)
        if user is not None:
            # Username/name yangilangan bo'lishi mumkin
            updated = False
            if username and user.username != username:
                user.username = username
                updated = True
            if full_name and user.full_name != full_name:
                user.full_name = full_name
                updated = True
            if updated:
                await self.session.flush()
            return user, False

        user = await self.create(
            tg_id=tg_id,
            username=username,
            full_name=full_name,
            language=language,
        )
        return user, True

    async def get_with_subscriptions(self, tg_id: int) -> User | None:
        """User + uning subscriptionlari (eager load)."""
        stmt = (
            select(User)
            .where(User.tg_id == tg_id)
            .options(selectinload(User.subscriptions))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_blocked(self, tg_id: int) -> None:
        """Bot bloklanganini belgilash (ForbiddenError)."""
        user = await self.get_by_tg_id(tg_id)
        if user:
            user.is_blocked = True
            await self.session.flush()

    async def list_active(self, *, limit: int | None = None) -> list[User]:
        """is_blocked=False bo'lgan userlar."""
        stmt = select(User).where(User.is_blocked.is_(False))
        if limit:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
