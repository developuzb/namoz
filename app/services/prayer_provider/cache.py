"""In-memory TTL cache (1 soat) — RAM da, restart da yo'qoladi."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Hashable

from app.core.constants import PROVIDER_CACHE_TTL
from app.core.logger import logger
from app.services.prayer_provider.base import PrayerTimes


@dataclass(slots=True)
class _Entry:
    value: PrayerTimes
    expires_at: datetime


class PrayerTimesCache:
    """Per-(provider, region_id, date) async-safe TTL cache."""

    def __init__(self, ttl_seconds: int = PROVIDER_CACHE_TTL) -> None:
        self._ttl = ttl_seconds
        self._store: dict[tuple[str, Hashable, date], _Entry] = {}
        self._lock = asyncio.Lock()

    async def get(
        self, provider: str, region_id: Hashable, target_date: date
    ) -> PrayerTimes | None:
        key = (provider, region_id, target_date)
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if datetime.now(UTC) >= entry.expires_at:
                del self._store[key]
                return None
            return entry.value

    async def set(self, value: PrayerTimes, region_id: Hashable) -> None:
        key = (value.provider, region_id, value.target_date)
        expires = datetime.now(UTC) + timedelta(seconds=self._ttl)
        async with self._lock:
            self._store[key] = _Entry(value=value, expires_at=expires)

    async def clear(self) -> None:
        async with self._lock:
            count = len(self._store)
            self._store.clear()
        logger.info("Prayer cache tozalandi ({} ta yozuv)", count)

    async def size(self) -> int:
        async with self._lock:
            return len(self._store)
