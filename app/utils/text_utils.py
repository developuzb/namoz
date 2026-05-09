"""Matn va HTML formatlash uchun yordamchi funksiyalar."""
from __future__ import annotations

import html
from datetime import datetime

from app.core.constants import MONTHS_UZ, WEEKDAYS_UZ


def escape_html(text: str | None) -> str:
    """HTML maxsus belgilarini xavfsiz qilib o'tkazish (Telegram caption uchun)."""
    if not text:
        return ""
    return html.escape(str(text), quote=False)


def format_milodiy_uz(dt: datetime) -> str:
    """
    O'zbekcha milodiy sana.

    >>> format_milodiy_uz(datetime(2026, 5, 8))
    '8-may, 2026'
    """
    return f"{dt.day}-{MONTHS_UZ[dt.month]}, {dt.year}"


def weekday_uz(dt: datetime) -> str:
    """
    O'zbekcha hafta kuni.

    >>> weekday_uz(datetime(2026, 5, 8))
    'Juma'
    """
    return WEEKDAYS_UZ[dt.weekday()]


def normalize_channel_link(link: str | None) -> str:
    """
    Kanal havolasini standart `https://t.me/...` formatga keltiradi.

    Misollar:
        "@qarshi"             -> "https://t.me/qarshi"
        "t.me/qarshi"         -> "https://t.me/qarshi"
        "https://t.me/qarshi" -> (o'zgarmaydi)
        "" / None             -> ""
    """
    if not link:
        return ""

    s = str(link).strip()
    if not s:
        return ""

    if s.startswith("@"):
        return f"https://t.me/{s[1:]}"
    if s.startswith(("http://t.me/", "https://t.me/")):
        return s
    if s.startswith("t.me/"):
        return f"https://{s}"
    return s


def truncate(text: str, max_len: int = 100, suffix: str = "...") -> str:
    """Uzun matnni qisqartirish (log uchun)."""
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix