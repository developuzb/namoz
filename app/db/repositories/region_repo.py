"""Region repository — hududlar ustida CRUD."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models.region import Region
from app.db.repositories.base import BaseRepository


class RegionRepository(BaseRepository[Region]):
    model = Region

    async def get_by_slug(self, slug: str) -> Region | None:
        return await self.get_by(slug=slug)

    async def get_by_name(self, name: str) -> Region | None:
        return await self.get_by(name=name)

    async def list_active(self, *, with_children: bool = False) -> list[Region]:
        """Faqat is_active=True bo'lgan, parent_id IS NULL (viloyatlar) yoki barcha."""
        stmt = select(Region).where(Region.is_active.is_(True)).order_by(Region.name)
        if with_children:
            stmt = stmt.options(selectinload(Region.children))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_children(self, parent_id: int) -> list[Region]:
        """Berilgan viloyatning tumanlari."""
        stmt = (
            select(Region)
            .where(Region.parent_id == parent_id, Region.is_active.is_(True))
            .order_by(Region.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_top_level(self) -> list[Region]:
        """parent_id IS NULL — viloyatlar ro'yxati."""
        stmt = (
            select(Region)
            .where(Region.parent_id.is_(None), Region.is_active.is_(True))
            .order_by(Region.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
