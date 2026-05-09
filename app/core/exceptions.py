"""Custom exception lar — clean error handling uchun."""
from __future__ import annotations


class TaqvimBotError(Exception):
    """Loyihaning barcha xatolari uchun bazaviy klass."""


# ============== Provider ==============


class ProviderError(TaqvimBotError):
    """Vaqt provideri bilan bog'liq umumiy xato."""


class ProviderTimeoutError(ProviderError):
    """Provider so'rov vaqti tugadi."""


class ProviderUnavailableError(ProviderError):
    """Provider hozir mavjud emas (HTTP 5xx, network)."""


class ProviderParseError(ProviderError):
    """Provider javobi noto'g'ri formatda."""


class RegionNotFoundError(ProviderError):
    """Provider da bu hudud topilmadi."""

    def __init__(self, region: str):
        self.region = region
        super().__init__(f"Hudud topilmadi: {region}")


# ============== Database ==============


class DatabaseError(TaqvimBotError):
    """DB bilan bog'liq xato."""


class NotFoundError(DatabaseError):
    """Yozuv topilmadi."""


class AlreadyExistsError(DatabaseError):
    """Bunday yozuv allaqachon mavjud."""


# ============== Validation ==============


class ValidationError(TaqvimBotError):
    """Foydalanuvchi kiritmasi noto'g'ri."""


class InvalidTimeFormatError(ValidationError):
    """Vaqt formati noto'g'ri (HH:MM kutilgan)."""

    def __init__(self, value: str):
        super().__init__(f"Vaqt formati noto'g'ri: {value!r}. Kutilgan: HH:MM")


# ============== Permissions ==============


class PermissionDeniedError(TaqvimBotError):
    """Foydalanuvchining huquqi yo'q."""
