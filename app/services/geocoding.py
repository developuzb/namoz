"""Reverse geocoding — lat/lon → joy nomi (Nominatim/OSM, bepul)."""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.exceptions import ProviderError
from app.core.logger import logger

#: Nominatim ToS — User-Agent majburiy + maks 1 req/sec
_USER_AGENT = "TaqvimBot/1.0 (https://t.me)"
_BASE_URL = "https://nominatim.openstreetmap.org"
_DEFAULT_TIMEOUT = 10


@dataclass(frozen=True, slots=True)
class GeoLocation:
    """Reverse geocode natijasi."""

    display_name: str          # to'liq matn ("Toshkent, O'zbekiston")
    city: str | None           # eng yaqin shahar/qishloq nomi
    country: str | None        # mamlakat
    latitude: float
    longitude: float

    @property
    def short_name(self) -> str:
        """Foydalanuvchiga ko'rsatish uchun qisqa nom."""
        if self.city and self.country:
            return f"{self.city}, {self.country}"
        if self.city:
            return self.city
        if self.country:
            return self.country
        return f"{self.latitude:.3f}, {self.longitude:.3f}"


class GeocodingError(ProviderError):
    """Geocoding xatosi."""


async def reverse_geocode(
    latitude: float,
    longitude: float,
    *,
    language: str = "uz,en",
) -> GeoLocation:
    """
    lat/lon → joy nomi (Nominatim).

    Args:
        latitude, longitude: koordinatalar
        language: `Accept-Language` (default 'uz,en' — o'zbekcha bo'lsa shu, yo'q bo'lsa inglizcha)

    Returns:
        GeoLocation

    Raises:
        GeocodingError: tarmoq xatosi yoki noto'g'ri javob.
    """
    url = f"{_BASE_URL}/reverse"
    params = {
        "lat": str(latitude),
        "lon": str(longitude),
        "format": "json",
        "accept-language": language,
        "zoom": "10",  # shahar darajasi
    }
    headers = {"User-Agent": _USER_AGENT}

    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException as e:
        raise GeocodingError(f"Nominatim timeout: {e}") from e
    except httpx.HTTPStatusError as e:
        raise GeocodingError(f"Nominatim HTTP {e.response.status_code}") from e
    except httpx.RequestError as e:
        raise GeocodingError(f"Nominatim network: {e}") from e
    except ValueError as e:
        raise GeocodingError(f"Nominatim noto'g'ri JSON: {e}") from e

    if not isinstance(data, dict) or "error" in data:
        raise GeocodingError(f"Nominatim xato: {data}")

    address = data.get("address") or {}
    display_name = data.get("display_name") or ""

    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("hamlet")
        or address.get("municipality")
        or address.get("county")
        or None
    )
    country = address.get("country") or None

    location = GeoLocation(
        display_name=display_name,
        city=city,
        country=country,
        latitude=latitude,
        longitude=longitude,
    )
    logger.debug(
        "Geocode {:.4f},{:.4f} → city={!r}, country={!r}",
        latitude, longitude, city, country,
    )
    return location


__all__ = ["GeoLocation", "GeocodingError", "reverse_geocode"]
