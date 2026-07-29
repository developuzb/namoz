"""DB tekshirish — parent va tumanlar masjid_times yozuvlari."""
from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.db.session import get_session


async def main() -> None:
    async with get_session() as s:
        r = await s.execute(
            text(
                "SELECT r.name, mt.prayer, mt.time "
                "FROM masjid_times mt "
                "JOIN regions r ON r.id = mt.region_id "
                "WHERE r.slug = 'qashqadaryo'"
            )
        )
        print("Parent (Qashqadaryo viloyati) yozuvlari:")
        for row in r:
            print(f"  {row[0]} | {row[1]} = {row[2]}")

        r = await s.execute(
            text(
                "SELECT COUNT(*) "
                "FROM masjid_times mt "
                "JOIN regions r ON r.id = mt.region_id "
                "WHERE r.parent_id IS NOT NULL"
            )
        )
        cnt = r.scalar()
        print(f"\nTumanlardagi yozuvlar soni: {cnt} (kutilgan: 0)")


if __name__ == "__main__":
    asyncio.run(main())
