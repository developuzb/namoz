"""Provider abstrakt interface va data class."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, date, datetime


@dataclass(frozen=True, slots=True)
class PrayerTimes:
    """Bir kun uchun namoz vaqtlari (immutable value object)."""

    region_label: str
    target_date: date
    times: dict[str, str]
    provider: str
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    #: IANA timezone (provider qaytargan bo'lsa, masalan Aladhan meta.timezone)
    timezone: str | None = None

    def get(self, prayer: str) -> str | None:
        return self.times.get(prayer)

    def has(self, prayer: str) -> bool:
        return bool(self.times.get(prayer))


class PrayerProvider(ABC):
    """Barcha namoz vaqti provider lar uchun bazaviy interface."""

    name: str

    @abstractmethod
    async def fetch(self, region_key: str | int, target_date: date) -> PrayerTimes:
        """Berilgan hudud va kun uchun vaqtlarni qaytaradi.

        Raises:
            ProviderTimeoutError: timeout
            ProviderUnavailableError: HTTP 5xx / network
            ProviderParseError: javob formati noto'g'ri
            RegionNotFoundError: hudud topilmadi
        """
        ...
