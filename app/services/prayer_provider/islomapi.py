"""islomapi.uz provider — PRIMARY (JSON API).

Endpoint: GET /api/monthly?region=<Name>&month=<int>
Javob — oyning har kuni uchun array.
"""
from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.constants import ALL_PRAYERS, PROVIDER_LABEL_MAP
from app.core.exceptions import (
    ProviderParseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    RegionNotFoundError,
)
from app.core.logger import logger
from app.services.prayer_provider.base import PrayerProvider, PrayerTimes
from app.utils.time_utils import clean_hhmm


class IslomapiProvider(PrayerProvider):
    """https://islomapi.uz/api/monthly?region=<Name>&month=<int>

    Javob shakli (har kun uchun):
        {
          "region": "Qarshi", "month": 5, "day": 1,
          "weekday": "Payshanba",
          "hijri_date": {"month": "...", "day": 3},
          "times": {
            "tong_saharlik": "04:14", "quyosh": "05:39",
            "peshin": "12:34", "asr": "17:27",
            "shom_iftor": "19:32", "hufton": "20:54"
          }
        }
    """

    name = "islomapi"

    def __init__(self, base_url: str | None = None, timeout: int | None = None) -> None:
        s = get_settings()
        self.base_url = (base_url or s.ISLOMAPI_BASE_URL).rstrip("/")
        self.timeout = timeout or s.PROVIDER_TIMEOUT

    async def fetch(self, region_key: str | int, target_date: date) -> PrayerTimes:
        if not isinstance(region_key, str):
            raise ValueError("islomapi region_key matn (provider_name) bo'lishi kerak")

        url = f"{self.base_url}/api/monthly"
        params = {"region": region_key, "month": str(target_date.month)}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                if response.status_code == 404:
                    raise RegionNotFoundError(region_key)
                response.raise_for_status()
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError(f"islomapi timeout: {url}") from e
        except httpx.HTTPStatusError as e:
            raise ProviderUnavailableError(f"islomapi HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise ProviderUnavailableError(f"islomapi network: {e}") from e

        try:
            payload = response.json()
        except ValueError as e:
            raise ProviderParseError(f"islomapi: noto'g'ri JSON: {e}") from e

        # islomapi noma'lum hudud uchun [] qaytaradi (200 OK bilan)
        if isinstance(payload, list) and not payload:
            raise RegionNotFoundError(region_key)

        day_record = self._find_day(payload, target_date.day)
        if day_record is None:
            raise ProviderParseError(
                f"islomapi: oy {target_date.month}, kun {target_date.day} topilmadi "
                f"(region={region_key})"
            )

        raw_times = day_record.get("times")
        if not isinstance(raw_times, dict):
            raise ProviderParseError(f"islomapi: 'times' dict emas (region={region_key})")

        normalized = self._normalize(raw_times)
        if not normalized:
            raise ProviderParseError(
                f"islomapi: vaqtlar bo'sh (region={region_key}, day={target_date.day})"
            )

        logger.debug(
            "islomapi[{}] {} kun uchun {} ta vaqt: {}",
            region_key, target_date, len(normalized), list(normalized.keys()),
        )

        return PrayerTimes(
            region_label=region_key,
            target_date=target_date,
            times=normalized,
            provider=self.name,
        )

    async def fetch_month_raw(
        self, region_key: str, year: int, month: int
    ) -> dict[int, dict[str, str]]:
        """Oyning barcha kunlari uchun vaqtlarni qaytaradi: {day: {prayer: time}}.

        islomapi.uz API faqat oy parametrini oladi (yil yo'q — joriy yil ishlatiladi),
        shu sababli `year` argumenti hozircha ishlatilmaydi.
        """
        url = f"{self.base_url}/api/monthly"
        params = {"region": region_key, "month": str(month)}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError(f"islomapi monthly timeout: {url}") from e
        except httpx.HTTPStatusError as e:
            raise ProviderUnavailableError(
                f"islomapi HTTP {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise ProviderUnavailableError(f"islomapi network: {e}") from e

        try:
            payload = response.json()
        except ValueError as e:
            raise ProviderParseError(f"islomapi: noto'g'ri JSON: {e}") from e

        if not isinstance(payload, list) or not payload:
            raise RegionNotFoundError(region_key)

        out: dict[int, dict[str, str]] = {}
        for record in payload:
            if not isinstance(record, dict):
                continue
            day = record.get("day")
            raw_times = record.get("times")
            if not isinstance(day, int) or not isinstance(raw_times, dict):
                continue
            normalized = self._normalize(raw_times)
            if normalized:
                out[day] = normalized
        return out

    @staticmethod
    def _find_day(payload: Any, day: int) -> dict[str, Any] | None:
        """Oy javobi ichidan kerakli kunni topish."""
        if not isinstance(payload, list):
            raise ProviderParseError("islomapi: javob list emas")
        for record in payload:
            if isinstance(record, dict) and record.get("day") == day:
                return record
        return None

    @staticmethod
    def _normalize(raw: dict[str, Any]) -> dict[str, str]:
        """`tong_saharlik` → `Bomdod` + HH:MM tozalash."""
        out: dict[str, str] = {}
        for raw_key, raw_value in raw.items():
            if not isinstance(raw_value, str):
                continue
            label = PROVIDER_LABEL_MAP.get(raw_key) or PROVIDER_LABEL_MAP.get(raw_key.lower())
            if not label or label not in ALL_PRAYERS:
                continue
            cleaned = clean_hhmm(raw_value)
            if cleaned:
                out[label] = cleaned
        return out
