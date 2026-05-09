"""DB ni tekshirish."""
import asyncio
from app.db.session import get_session
from app.db.repositories import RegionRepository, MasjidTimeRepository


async def main():
    async with get_session() as s:
        rr = RegionRepository(s)
        all_regions = await rr.list_all()
        print(f"\n📍 Jami hududlar: {len(all_regions)}\n")

        viloyat = await rr.get_by_slug("qashqadaryo")
        print(f"🏛  Viloyat: {viloyat.name} (id={viloyat.id})\n")

        tumanlar = await rr.list_children(viloyat.id)
        print(f"🏘  Tumanlar ({len(tumanlar)}):")
        for t in tumanlar:
            print(f"    • {t.name}")

        # Masjid vaqtlari
        qarshi = await rr.get_by_slug("qarshi")
        mr = MasjidTimeRepository(s)
        times = await mr.get_for_region(qarshi.id)
        print(f"\n🕌 {qarshi.name} masjid vaqtlari:")
        for prayer, time in times.items():
            print(f"    {prayer:8s} → {time}")

        print("\n✅ DB to'g'ri ishlayapti!")


asyncio.run(main())