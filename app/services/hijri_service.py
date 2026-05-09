"""Hijriy sana — `hijri-converter` ustida o'zbekcha qatlam."""
from __future__ import annotations

from datetime import date

from hijri_converter import Gregorian

from app.core.constants import HIJRI_MONTHS_UZ
from app.core.logger import logger


def gregorian_to_hijri_uz(gdate: date) -> str:
    """
    Milodiy sanani o'zbekcha hijriy formatga aylantiradi.

    >>> gregorian_to_hijri_uz(date(2026, 5, 9))
    "23-shavvol, 1447-hijriy"
    """
    try:
        h = Gregorian(gdate.year, gdate.month, gdate.day).to_hijri()
    except (ValueError, OverflowError) as e:
        logger.error("Hijri konvert xatosi {}: {}", gdate, e)
        return "—"

    month_name = HIJRI_MONTHS_UZ.get(h.month, h.month_name() if hasattr(h, "month_name") else "?")
    return f"{h.day}-{month_name}, {h.year}-hijriy"


__all__ = ["gregorian_to_hijri_uz"]
