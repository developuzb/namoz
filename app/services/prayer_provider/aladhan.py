"""Aladhan API — global provider (lat/lon ko'rinishida).

https://api.aladhan.com/v1/timings/{date}?latitude=X&longitude=Y&method=N&school=N
Bepul, kalit kerak emas, har joyda ishlaydi.

Method namunalari:
  2 — Islamic Society of North America (ISNA) — default
  3 — Muslim World League (MWL)
  5 — Egyptian General Authority of Survey
  7 — Institute of Geophysics, University of Tehran
  13 — Diyanet İşleri Başkanlığı, Turkey

School:
  0 — Shafi/Maliki/Hanbali (default Aladhan)
  1 — Hanafi (Asr kech tushadi)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.constants import ALL_PRAYERS
from app.core.exceptions import (
    ProviderParseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.core.logger import logger
from app.services.prayer_provider.base import PrayerProvider, PrayerTimes
from app.utils.time_utils import clean_hhmm

#: Aladhan kalitlarni standart o'zbek nomlariga aylantirish
_LABEL_MAP: dict[str, str] = {
    "Fajr":     "Bomdod",
    "Sunrise":  "Quyosh",
    "Dhuhr":    "Peshin",
    "Asr":      "Asr",
    "Maghrib":  "Shom",
    "Isha":     "Xufton",
}


@dataclass(frozen=True, slots=True)
class GeoPoint:
    """Aladhan uchun region_key sifatida ishlatiladi (lat + lon + method + school)."""

    latitude: float
    longitude: float
    method: int = 2
    school: int = 1


class AladhanProvider(PrayerProvider):
    """https://aladhan.com — yer yuzining istalgan koordinatasi uchun namoz vaqti."""

    name = "aladhan"

    def __init__(self, base_url: str = "https://api.aladhan.com", timeout: int | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout or get_settings().PROVIDER_TIMEOUT

    async def fetch(self, region_key: GeoPoint, target_date: date) -> PrayerTimes:  # type: ignore[override]
        if not isinstance(region_key, GeoPoint):
            raise ValueError("aladhan region_key GeoPoint bo'lishi kerak")

        # Aladhan sana formati: DD-MM-YYYY
        date_str = target_date.strftime("%d-%m-%Y")
        url = f"{self.base_url}/v1/timings/{date_str}"
        params = {
            "latitude": str(region_key.latitude),
            "longitude": str(region_key.longitude),
            "method": str(region_key.method),
            "school": str(region_key.school),
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError(f"aladhan timeout: {url}") from e
        except httpx.HTTPStatusError as e:
            raise ProviderUnavailableError(f"aladhan HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise ProviderUnavailableError(f"aladhan network: {e}") from e

        try:
            payload = response.json()
        except ValueError as e:
            raise ProviderParseError(f"aladhan: noto'g'ri JSON: {e}") from e

        timings = self._extract_timings(payload)
        normalized = self._normalize(timings)
        tz_name = self._extract_timezone(payload)

        if not normalized:
            raise ProviderParseError(
                f"aladhan: vaqtlar topilmadi (lat={region_key.latitude}, lon={region_key.longitude})"
            )

        logger.debug(
            "aladhan[{:.2f},{:.2f}] {} kun uchun {} ta vaqt, tz={}",
            region_key.latitude, region_key.longitude,
            target_date, len(normalized), tz_name,
        )

        return PrayerTimes(
            region_label=f"{region_key.latitude:.4f},{region_key.longitude:.4f}",
            target_date=target_date,
            times=normalized,
            provider=self.name,
            timezone=tz_name,
        )

    @staticmethod
    def _extract_timezone(payload: Any) -> str | None:
        """Aladhan meta.timezone (masalan 'Asia/Tashkent')."""
        if not isinstance(payload, dict):
            return None
        data = payload.get("data") or {}
        meta = data.get("meta") if isinstance(data, dict) else None
        if isinstance(meta, dict):
            tz = meta.get("timezone")
            if isinstance(tz, str) and tz:
                return tz
        return None

    @staticmethod
    def _extract_timings(payload: Any) -> dict[str, str]:
        if not isinstance(payload, dict):
            raise ProviderParseError("aladhan: javob dict emas")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ProviderParseError("aladhan: 'data' yo'q")
        timings = data.get("timings")
        if not isinstance(timings, dict):
            raise ProviderParseError("aladhan: 'timings' yo'q")
        return {k: str(v) for k, v in timings.items() if isinstance(v, str)}

    @staticmethod
    def _normalize(timings: dict[str, str]) -> dict[str, str]:
        out: dict[str, str] = {}
        for raw_key, raw_value in timings.items():
            label = _LABEL_MAP.get(raw_key)
            if not label or label not in ALL_PRAYERS:
                continue
            # "03:42 (UZT)" — qavs ichidagi tz tag'ini olib tashlash
            cleaned = clean_hhmm(raw_value.split(" ")[0])
            if cleaned:
                out[label] = cleaned
        return out


__all__ = ["AladhanProvider", "GeoPoint"]
