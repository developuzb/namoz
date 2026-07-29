"""MasjidTime repository — masjid jamoat vaqtlari."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.core.constants import FARZ_PRAYERS
from app.db.models.masjid_time import MasjidTime
from app.db.repositories.base import BaseRepository


class MasjidTimeRepository(BaseRepository[MasjidTime]):
    model = MasjidTime

    async def get_for_region(self, region_id: int) -> dict[str, str]:
        """
        Hudud uchun barcha namozlar dict: {"Bomdod": "07:00", ...}.

        Agar yozuv yo'q bo'lsa — bo'sh dict.
        """
        stmt = select(MasjidTime).where(MasjidTime.region_id == region_id)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return {row.prayer: row.time for row in rows}

    async def upsert(
        self,
        region_id: int,
        prayer: str,
        time: str,
        *,
        updated_by_tg_id: int | None = None,
    ) -> MasjidTime:
        """
        Vaqtni o'rnatish (mavjud bo'lsa yangilash, yo'q bo'lsa yaratish).

        ON CONFLICT DO UPDATE — SQLite (lokal) va PostgreSQL (Heroku) ikkalasi
        ham qo'llaydi; drayver dialektiga qarab to'g'ri `insert` tanlanadi.
        """
        if prayer not in FARZ_PRAYERS:
            raise ValueError(f"Faqat farz namozlari ruxsat etilgan: {FARZ_PRAYERS}")

        from app.core.config import get_settings

        insert = pg_insert if get_settings().is_postgres else sqlite_insert

        stmt = (
            insert(MasjidTime)
            .values(
                region_id=region_id,
                prayer=prayer,
                time=time,
                updated_by_tg_id=updated_by_tg_id,
            )
            .on_conflict_do_update(
                index_elements=["region_id", "prayer"],
                set_={"time": time, "updated_by_tg_id": updated_by_tg_id},
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

        # Yangi/yangilangan obyektni qaytaramiz
        existing = await self.get_by(region_id=region_id, prayer=prayer)
        assert existing is not None
        return existing

    async def bulk_upsert(
        self,
        region_id: int,
        times: dict[str, str],
        *,
        updated_by_tg_id: int | None = None,
    ) -> None:
        """Bir hudud uchun bir nechta vaqtni birdan o'rnatish."""
        for prayer, time in times.items():
            if prayer in FARZ_PRAYERS:
                await self.upsert(region_id, prayer, time, updated_by_tg_id=updated_by_tg_id)
