"""Admin filter — handler larni faqat adminlar uchun cheklash."""
from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject


class AdminFilter(BaseFilter):
    """
    `data["is_admin"]` True bo'lsa o'tkazadi.
    Bu qiymat `UserRegisterMiddleware` tomonidan o'rnatiladi.
    """

    async def __call__(self, event: TelegramObject, is_admin: bool = False) -> bool:
        return is_admin
