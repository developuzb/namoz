"""praytime.uz provider — FALLBACK (HTML scrape)."""
from __future__ import annotations

import re
from datetime import date

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.core.constants import ALL_PRAYERS, PROVIDER_LABEL_MAP
from app.core.exceptions import (
    ProviderParseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.core.logger import logger
from app.services.prayer_provider.base import PrayerProvider, PrayerTimes
from app.utils.time_utils import clean_hhmm

# "00:58:35" — keyingi namoz countdown formati (HH:MM:SS)
_COUNTDOWN_RE = re.compile(r"^\d{1,2}:\d{2}:\d{2}$")


class PraytimeProvider(PrayerProvider):
    """https://praytime.uz/?region_id=<int>&lng=uz — HTML sahifadan parse."""

    name = "praytime"

    _USER_AGENT = "Mozilla/5.0 (compatible; TaqvimBot/1.0)"

    def __init__(self, base_url: str | None = None, timeout: int | None = None) -> None:
        s = get_settings()
        self.base_url = (base_url or s.PRAYTIME_BASE_URL).rstrip("/")
        self.timeout = timeout or s.PROVIDER_TIMEOUT

    async def fetch(self, region_key: str | int, target_date: date) -> PrayerTimes:
        if not isinstance(region_key, int):
            raise ValueError("praytime region_key int (praytime_id) bo'lishi kerak")

        url = f"{self.base_url}/"
        params = {"region_id": str(region_key), "lng": "uz"}

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, follow_redirects=True
            ) as client:
                response = await client.get(
                    url, params=params, headers={"User-Agent": self._USER_AGENT}
                )
                response.raise_for_status()
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError(f"praytime timeout: {url}") from e
        except httpx.HTTPStatusError as e:
            raise ProviderUnavailableError(
                f"praytime HTTP {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise ProviderUnavailableError(f"praytime network: {e}") from e

        times = self._parse_html(response.text)

        if not times:
            raise ProviderParseError(
                f"praytime: HTML da .prayer-times topilmadi (region_id={region_key})"
            )

        logger.debug(
            "praytime[{}] {} ta vaqt qaytardi: {}",
            region_key, len(times), list(times.keys()),
        )

        return PrayerTimes(
            region_label=str(region_key),
            target_date=target_date,
            times=times,
            provider=self.name,
        )

    @staticmethod
    def _parse_html(html: str) -> dict[str, str]:
        """`.prayer-times` bloklaridan label+vaqtni ajratib olish.

        Praytime saytida "keyingi namoz" bloki uchun rollar almashadi:
            normal:    <b>Tong</b>      <div.time>04:03</div>
            keyingisi: <b>00:58:35</b>  <div.time>Xufton</div>  <div.countdown-time>21:05</div>

        Shu sababli avval countdown formatini tekshirib, kerak bo'lsa
        label/time ni almashtirib olamiz.
        """
        soup = BeautifulSoup(html, "lxml")
        out: dict[str, str] = {}

        for block in soup.select(".prayer-times"):
            b_tag = block.find("b")
            time_div = block.find("div", class_="time")
            countdown_div = block.find("div", class_="countdown-time")
            if not b_tag or not time_div:
                continue

            b_text = b_tag.get_text(strip=True)
            time_text = time_div.get_text(strip=True)

            if _COUNTDOWN_RE.match(b_text):
                # "Keyingi namoz" bloki — rollar almashgan
                raw_label = time_text
                raw_value = (
                    countdown_div.get_text(strip=True) if countdown_div else ""
                )
            else:
                raw_label = b_text
                raw_value = time_text

            label = PROVIDER_LABEL_MAP.get(raw_label)
            if not label or label not in ALL_PRAYERS:
                continue

            cleaned = clean_hhmm(raw_value)
            if cleaned:
                out[label] = cleaned

        return out
