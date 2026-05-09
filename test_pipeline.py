"""End-to-end smoke test: provider → nafl → hijri → image → caption."""
import asyncio
from datetime import date, datetime

import pytz

from app.core.config import get_settings
from app.db.repositories import MasjidTimeRepository, RegionRepository
from app.db.session import get_session
from app.services.caption_builder import build_post_caption
from app.services.hijri_service import gregorian_to_hijri_uz
from app.services.image_builder import make_prayer_image
from app.services.prayer_provider import PrayerService
from app.services.time_calculator import (
    calculate_nafl_windows,
    get_current_nafl_status,
)


async def main():
    settings = get_settings()
    tz = pytz.timezone(settings.TIMEZONE)
    today = date.today()
    now = datetime.now(tz)

    # ---- 1. DB: Qarshi va uning masjid vaqtlari ----
    async with get_session() as s:
        rr = RegionRepository(s)
        mr = MasjidTimeRepository(s)
        qarshi = await rr.get_by_slug("qarshi")
        viloyat = await rr.get_or_raise(qarshi.parent_id)
        masjid_times = await mr.get_for_region(qarshi.id)

    # ---- 2. Provider ----
    service = PrayerService()
    pt = await service.fetch_for_region(qarshi, today)
    print(f"\n[provider] {pt.provider} → {len(pt.times)} ta vaqt")

    # ---- 3. Nafl ----
    nafl = calculate_nafl_windows(
        region_times=pt.times,
        masjid_times=masjid_times,
        target_date=today,
        tz=tz,
    )
    print(f"\n[nafl windows]")
    for k, v in nafl.items():
        print(f"  {k:10s} {v}")

    status = get_current_nafl_status(
        region_times=pt.times, target_date=today, tz=tz, now=now
    )
    print(f"\n[nafl status]\n  {status}")

    # ---- 4. Hijri ----
    hijriy = gregorian_to_hijri_uz(today)
    print(f"\n[hijri] {today} → {hijriy}")

    # ---- 5. Image ----
    from app.utils.text_utils import format_milodiy_uz
    milodiy = format_milodiy_uz(datetime(today.year, today.month, today.day))
    img_path = make_prayer_image(
        region_name=qarshi.name,
        milodiy=milodiy,
        hijriy=hijriy,
        region_times=pt.times,
        masjid_times=masjid_times,
    )
    print(f"\n[image] {img_path}  ({img_path.stat().st_size // 1024} KB)")

    # ---- 6. Caption ----
    caption = build_post_caption(
        parent_region_name=viloyat.name.replace(" viloyati", ""),
        region_name=qarshi.name,
        target_date=today,
        hijriy=hijriy,
        nafl_windows=nafl,
        region_times=pt.times,
        masjid_times=masjid_times,
        channel_link="@qarshi_masjidi",
    )
    print(f"\n[caption] ({len(caption)} belgi)\n{'-' * 60}")
    print(caption)
    print("-" * 60)


asyncio.run(main())
