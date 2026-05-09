"""PrayerService — provider chain orchestrator (cache + fallback)."""
from __future__ import annotations

from datetime import date

from app.core.config import get_settings
from app.core.exceptions import ProviderError
from app.core.logger import logger
from app.db.models.region import Region
from app.services.prayer_provider.aladhan import AladhanProvider, GeoPoint
from app.services.prayer_provider.base import PrayerTimes
from app.services.prayer_provider.cache import PrayerTimesCache
from app.services.prayer_provider.islomapi import IslomapiProvider
from app.services.prayer_provider.praytime import PraytimeProvider


class PrayerService:
    """
    Hudud uchun namoz vaqtini olish strategiyasi:

    1. Cache (RAM, 1 soat TTL) ga qarash
    2. PRIMARY provider — odatda islomapi (region.provider_name)
    3. FALLBACK provider — praytime (region.praytime_id)
    4. GLOBAL provider — aladhan (region.latitude/longitude) — dunyoning istalgan joyida
    5. Hammasi xato → ProviderError ko'tariladi (post o'tkazib yuboriladi)
    """

    def __init__(
        self,
        islomapi: IslomapiProvider | None = None,
        praytime: PraytimeProvider | None = None,
        aladhan: AladhanProvider | None = None,
        cache: PrayerTimesCache | None = None,
    ) -> None:
        self.islomapi = islomapi or IslomapiProvider()
        self.praytime = praytime or PraytimeProvider()
        self.aladhan = aladhan or AladhanProvider()
        self.cache = cache or PrayerTimesCache()

        s = get_settings()
        self._chain = self._build_chain(s.PRAYER_PROVIDER_PRIMARY, s.PRAYER_PROVIDER_FALLBACK)
        logger.info("PrayerService chain: {}", " → ".join(self._chain))

    @staticmethod
    def _build_chain(primary: str, fallback: str) -> list[str]:
        """Chain tartibi: primary, fallback, va oxirida global aladhan."""
        order: list[str] = []
        for name in (primary, fallback):
            if name in {"islomapi", "praytime"} and name not in order:
                order.append(name)
        if not order:
            order = ["islomapi", "praytime"]
        order.append("aladhan")  # global fallback har doim oxirida
        return order

    async def fetch_for_region(self, region: Region, target_date: date) -> PrayerTimes:
        """
        Hudud uchun vaqtlarni olish.

        Raises:
            ProviderError — barcha provider lar ishlamasa.
        """
        errors: list[str] = []

        for provider_name in self._chain:
            cached = await self.cache.get(provider_name, region.id, target_date)
            if cached is not None:
                logger.debug(
                    "Cache hit: {} / {} / {}", provider_name, region.name, target_date
                )
                return cached

            try:
                raw = await self._fetch_single(provider_name, region, target_date)
            except ProviderError as e:
                errors.append(f"{provider_name}: {e}")
                logger.debug(
                    "Provider {} ishlamadi (region={}): {}",
                    provider_name, region.name, e,
                )
                continue

            result = PrayerTimes(
                region_label=region.name,
                target_date=raw.target_date,
                times=raw.times,
                provider=raw.provider,
                timezone=raw.timezone,
            )
            await self.cache.set(result, region.id)
            return result

        raise ProviderError(
            f"Barcha provider lar {region.name} uchun ishlamadi: " + " | ".join(errors)
        )

    async def _fetch_single(
        self, provider_name: str, region: Region, target_date: date
    ) -> PrayerTimes:
        if provider_name == "islomapi":
            if not region.provider_name:
                raise ProviderError(
                    f"{region.name}: islomapi uchun provider_name yo'q (DB da NULL)"
                )
            return await self.islomapi.fetch(region.provider_name, target_date)

        if provider_name == "praytime":
            if not region.praytime_id:
                raise ProviderError(
                    f"{region.name}: praytime_id yo'q (DB da NULL)"
                )
            return await self.praytime.fetch(region.praytime_id, target_date)

        if provider_name == "aladhan":
            if region.latitude is None or region.longitude is None:
                raise ProviderError(
                    f"{region.name}: latitude/longitude yo'q (DB da NULL)"
                )
            geo = GeoPoint(
                latitude=region.latitude,
                longitude=region.longitude,
                method=region.aladhan_method,
                school=region.aladhan_school,
            )
            return await self.aladhan.fetch(geo, target_date)

        raise ProviderError(f"Noma'lum provider nomi: {provider_name}")
