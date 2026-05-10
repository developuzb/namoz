"""Hijriy bayramlar va alohida kunlarni aniqlash.

Ka'lendar mantiqi: hijri-converter orqali bugungi sananing hijriy versiyasini
olib, alohida bayramni yoki Ramazon kunini aniqlaymiz.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hijri_converter import Gregorian


@dataclass(frozen=True, slots=True)
class HijriHoliday:
    key: str
    name_uz: str
    greeting: str  # caption'ga qo'shiladigan asosiy matn
    icon: str = "🕌"


# ============== Bayramlar (hijri month, day) ==============
_HOLIDAYS: dict[tuple[int, int], HijriHoliday] = {
    (1, 1): HijriHoliday(
        key="hijri_new_year",
        name_uz="Hijriy yangi yil",
        greeting="🎊 <b>Hijriy yangi yil muborak bo'lsin!</b>",
        icon="🎊",
    ),
    (1, 10): HijriHoliday(
        key="ashura",
        name_uz="Ashura kuni",
        greeting=(
            "🕌 <b>Ashura kuni muborak!</b>\n"
            "<i>Bugun (Muharram 10) — Allohga rozalik tutish savobli.</i>"
        ),
    ),
    (3, 12): HijriHoliday(
        key="mavlud",
        name_uz="Mavlud — Payg'ambar (s.a.v.) tug'ilgan kun",
        greeting=(
            "🕌 <b>Mavlud muborak!</b>\n"
            "<i>Bugun Rabi'-ul-Avval 12 — Muhammad (s.a.v.) tug'ilgan kun.</i>"
        ),
    ),
    (7, 27): HijriHoliday(
        key="isra_miraj",
        name_uz="Isro va Mi'roj kechasi",
        greeting=(
            "🌌 <b>Isro va Mi'roj kechasi muborak!</b>\n"
            "<i>Rajab 27 — Payg'ambarimiz (s.a.v.) Quddusga olib borilib, "
            "samolarga ko'tarilgan muborak kecha.</i>"
        ),
    ),
    (8, 15): HijriHoliday(
        key="bara_a",
        name_uz="Bara'at kechasi",
        greeting=(
            "🌙 <b>Bara'at (mag'firat) kechasi muborak!</b>\n"
            "<i>Sha'bon 15 — duo va istig'for kechasi.</i>"
        ),
    ),
    (9, 1): HijriHoliday(
        key="ramadan_start",
        name_uz="Ramazon oyi boshlandi",
        greeting=(
            "🌙 <b>Ramazon oyi muborak bo'lsin!</b>\n"
            "<i>Roza tutish, Qur'on tilovati, kechasi qiyom va sadaqa oyi.</i>"
        ),
    ),
    (9, 27): HijriHoliday(
        key="laylat_al_qadr",
        name_uz="Laylatul Qadr — Qadr kechasi",
        greeting=(
            "✨ <b>Laylatul Qadr — Qadr kechasi muborak!</b>\n"
            "<i>«Qadr kechasi ming oydan yaxshidir.» (Qadr 97:3)</i>"
        ),
        icon="✨",
    ),
    (10, 1): HijriHoliday(
        key="eid_al_fitr",
        name_uz="Ramazon Hayiti — Eid-ul-Fitr",
        greeting=(
            "🎉 <b>Ramazon Hayiti muborak bo'lsin!</b>\n"
            "<i>Bayram namozini va sadaqa-i fitrni unutmang.</i>"
        ),
        icon="🎉",
    ),
    (12, 9): HijriHoliday(
        key="day_of_arafah",
        name_uz="Arafa kuni",
        greeting=(
            "🕋 <b>Arafa kuni muborak!</b>\n"
            "<i>Roza tutilsa, ikki yil gunohlari kechiriladi.</i>"
        ),
    ),
    (12, 10): HijriHoliday(
        key="eid_al_adha",
        name_uz="Qurbon Hayiti — Eid-ul-Adha",
        greeting=(
            "🎉 <b>Qurbon Hayiti muborak bo'lsin!</b>\n"
            "<i>Bayram namozini va qurbonlik sunnatini bajarish.</i>"
        ),
        icon="🎉",
    ),
}


def get_holiday(g_date: date) -> HijriHoliday | None:
    """Bugun hijriy bayrammi tekshiradi. None bo'lsa — oddiy kun."""
    try:
        h = Gregorian(g_date.year, g_date.month, g_date.day).to_hijri()
    except (ValueError, OverflowError):
        return None
    return _HOLIDAYS.get((h.month, h.day))


def get_ramadan_day(g_date: date) -> int | None:
    """Agar bugun Ramazon (hijriy oy=9), kun raqami (1–30). Aks holda None."""
    try:
        h = Gregorian(g_date.year, g_date.month, g_date.day).to_hijri()
    except (ValueError, OverflowError):
        return None
    if h.month == 9:
        return h.day
    return None


__all__ = [
    "HijriHoliday",
    "get_holiday",
    "get_ramadan_day",
]
