"""Generic repository — barcha CRUD metodlari uchun bazaviy klass."""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Bazaviy CRUD — har bir konkret repository undan meros oladi.

    Maqsad: handler/service da `session.execute(select(...))` yozishni minimallashtirish.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ============== Read ==============

    async def get(self, pk: int) -> ModelT | None:
        return await self.session.get(self.model, pk)

    async def get_or_raise(self, pk: int) -> ModelT:
        obj = await self.get(pk)
        if obj is None:
            raise NotFoundError(f"{self.model.__name__}(id={pk}) topilmadi")
        return obj

    async def get_by(self, **filters: Any) -> ModelT | None:
        stmt = select(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, *, limit: int | None = None, offset: int = 0) -> list[ModelT]:
        stmt = select(self.model).offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def filter_by(self, **filters: Any) -> list[ModelT]:
        stmt = select(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, **filters: Any) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self.model)
        if filters:
            stmt = stmt.filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # ============== Write ==============

    async def create(self, **data: Any) -> ModelT:
        obj = self.model(**data)
        self.session.add(obj)
        try:
            await self.session.flush()
        except IntegrityError as e:
            await self.session.rollback()
            raise AlreadyExistsError(f"{self.model.__name__}: {e.orig}") from e
        return obj

    async def update(self, obj: ModelT, **data: Any) -> ModelT:
        for key, value in data.items():
            setattr(obj, key, value)
        await self.session.flush()
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)
        await self.session.flush()

    async def delete_by(self, **filters: Any) -> int:
        stmt = delete(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.rowcount or 0
