"""Provider qatlamini tekshirish + 14 ta tumanni islomapi/praytime bo'yicha audit qilish."""
import asyncio
from datetime import date

from app.db.repositories import RegionRepository
from app.db.session import get_session
from app.services.prayer_provider import PrayerService


async def main():
    today = date.today()
    service = PrayerService()

    async with get_session() as s:
        rr = RegionRepository(s)
        viloyat = await rr.get_by_slug("qashqadaryo")
        tumanlar = await rr.list_children(viloyat.id)

    print(f"\n{'Tuman':<14}{'islomapi':<12}{'praytime':<12}{'natija':<12}")
    print("-" * 50)

    for region in tumanlar:
        try:
            pt = await service.fetch_for_region(region, today)
            n = len(pt.times)
            note = f"{pt.provider} ({n})"
        except Exception as e:
            note = f"FAIL: {type(e).__name__}"

        # Cache buzib alohida ham tekshiramiz: islomapi ishladi/yo'q
        await service.cache.clear()
        try:
            isl_pt = await service.islomapi.fetch(region.provider_name or "", today)
            isl = "OK"
        except Exception as e:
            isl = type(e).__name__

        try:
            pr_pt = await service.praytime.fetch(region.praytime_id or 0, today)
            pr = "OK"
        except Exception as e:
            pr = type(e).__name__

        print(f"{region.name:<14}{isl:<12}{pr:<12}{note:<12}")


asyncio.run(main())
