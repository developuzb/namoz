"""Bitta hudud uchun post yasash pipeline'i — kanal va DM ikkalasida ishlatiladi."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pytz
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import FARZ_PRAYERS
from app.db.models.region import Region
from app.db.repositories.masjid_time_repo import MasjidTimeRepository
from app.db.repositories.region_repo import RegionRepository
from app.services.caption_builder import build_post_caption
from app.services.hijri_service import gregorian_to_hijri_uz
from app.services.image_builder import make_prayer_image
from app.services.prayer_provider import PrayerService
from app.utils.text_utils import format_milodiy_uz
from app.utils.time_utils import parse_hhmm_to_dt


def _find_next_farz(
    times: dict[str, str], target_date: date, now: datetime, tz: pytz.BaseTzInfo
) -> str | None:
    """Bugungi farzlar ichidan keyingi (vaqti hali kelmagan) namozni topadi.
    Hammasi o'tib bo'lgan bo'lsa — None (ertaga Bomdod, lekin highlight qilmaymiz)."""
    for prayer in FARZ_PRAYERS:
        t = times.get(prayer)
        if not t:
            continue
        dt = parse_hhmm_to_dt(t, target_date, tz)
        if dt and dt > now:
            return prayer
    return None


_ATTRIBUTION = {
    "islomapi": "Hanafiy mazhabi uslubida",
    "praytime": "Hanafiy mazhabi uslubida",
    "aladhan":  "Hanafiy mazhabi (ISNA) uslubida",
}


@dataclass(frozen=True, slots=True)
class PostBundle:
    image_path: Path
    caption: str
    provider: str


class PostService:
    """Region uchun rasm + caption yasashning butun pipeline."""

    def __init__(self, prayer_service: PrayerService | None = None) -> None:
        self.prayer_service = prayer_service or PrayerService()

    async def build_for_region(
        self,
        *,
        session: AsyncSession,
        region: Region,
        target_date: date,
        channel_link: str | None = None,
        now: datetime | None = None,
    ) -> PostBundle:
        """
        Bitta hudud uchun to'liq post (rasm + caption) yasaydi.

        Raises:
            ProviderError: barcha provider lar ishlamasa.
        """
        settings = get_settings()
        tz = pytz.timezone(region.timezone or settings.TIMEZONE)
        now = now or datetime.now(tz)

        pt = await self.prayer_service.fetch_for_region(region, target_date)

        # Provider qaytargan IANA timezone'ni saqlab qo'yish (avtomatik to'g'rilash)
        if pt.timezone and (not region.timezone or region.timezone in {"UTC", ""}):
            from app.core.logger import logger
            logger.info(
                "Region {} timezone auto-set: {} -> {}",
                region.name, region.timezone, pt.timezone,
            )
            region.timezone = pt.timezone
            await session.flush()

        mr = MasjidTimeRepository(session)
        rr = RegionRepository(session)
        viloyat = await rr.get(region.parent_id) if region.parent_id else None
        parent_name = (viloyat.name if viloyat else "").replace(" viloyati", "")

        # Jamoat vaqtlari: avval tuman'ning o'zida, yo'q bo'lsa viloyat parent'da.
        # Viloyat darajasida bitta to'plam — adminlar bir joyda boshqaradi.
        masjid_times = await mr.get_for_region(region.id)
        if not masjid_times and viloyat is not None:
            masjid_times = await mr.get_for_region(viloyat.id)

        hijriy = gregorian_to_hijri_uz(target_date)
        milodiy = format_milodiy_uz(
            datetime(target_date.year, target_date.month, target_date.day)
        )

        next_farz = _find_next_farz(pt.times, target_date, now, tz)

        img_path = make_prayer_image(
            region_name=region.name,
            milodiy=milodiy,
            hijriy=hijriy,
            region_times=pt.times,
            masjid_times=masjid_times,
            highlight_prayer=next_farz,
        )

        caption = build_post_caption(
            parent_region_name=parent_name,
            region_name=region.name,
            target_date=target_date,
            hijriy=hijriy,
            region_times=pt.times,
            masjid_times=masjid_times,
            channel_link=channel_link,
            attribution=_ATTRIBUTION.get(pt.provider),
        )

        return PostBundle(image_path=img_path, caption=caption, provider=pt.provider)


__all__ = ["PostBundle", "PostService"]
