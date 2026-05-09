"""Vaqt parsing va formatlash uchun yordamchi funksiyalar."""
from __future__ import annotations

import re
from datetime import date, datetime, time

import pytz

#: "HH:MM" formatini tekshiruvchi regex
_TIME_RE = re.compile(r"^\s*\d{1,2}:\d{2}\s*$")


def clean_hhmm(value: str | None) -> str | None:
    """
    Vaqtni standart `HH:MM` formatga keltirish.

    Misollar:
        "17.22"      -> "17:22"
        "1722"       -> "17:22"
        "4:5"        -> "04:05"
        " 7 : 30 "   -> "07:30"
        "-" / "—"    -> None
        ""           -> None

    Returns:
        Tozalangan "HH:MM" string yoki None.
    """
    if not value:
        return None

    s = str(value).strip().replace(" ", "").replace(".", ":").replace("—", "-").replace("–", "-")
    if s in {"", "-", "--", "--:--"}:
        return None

    # "1722" -> "17:22"
    if s.isdigit() and len(s) in (3, 4):
        s = f"0{s[0]}:{s[1:]}" if len(s) == 3 else f"{s[:2]}:{s[2:]}"

    if ":" not in s:
        return None

    hh, _, mm = s.partition(":")
    if not (hh.isdigit() and mm.isdigit()):
        return None

    h, m = int(hh), int(mm)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None

    return f"{h:02d}:{m:02d}"


def parse_hhmm_to_dt(
    value: str | None,
    base_date: date,
    tz: pytz.BaseTzInfo,
) -> datetime | None:
    """
    "HH:MM" string ni tabiiy datetime ga aylantiradi (timezone bilan).

    Returns:
        Timezone-aware datetime yoki None (parse muvaffaqiyatsiz bo'lsa).
    """
    cleaned = clean_hhmm(value)
    if cleaned is None:
        return None

    h, m = map(int, cleaned.split(":"))
    naive = datetime.combine(base_date, time(hour=h, minute=m))
    return tz.localize(naive)


def format_eta(minutes: int) -> str:
    """
    Qolgan daqiqalarni o'qishga qulay matnga o'tkazish.

    Misollar:
        0   -> "≤1 daqiqa qoldi"
        25  -> "25 daqiqa qoldi"
        90  -> "1 soat 30 daqiqa qoldi"
        120 -> "2 soat qoldi"
    """
    if minutes <= 0:
        return "≤1 daqiqa qoldi"

    h, m = divmod(minutes, 60)
    if h == 0:
        return f"{m} daqiqa qoldi"
    if m == 0:
        return f"{h} soat qoldi"
    return f"{h} soat {m} daqiqa qoldi"


def now_in_tz(tz: pytz.BaseTzInfo) -> datetime:
    """Hozirgi vaqtni belgilangan tz da olish (qulay shortcut)."""
    return datetime.now(tz)


def is_time_passed(
    hhmm: str | None,
    base_date: date,
    tz: pytz.BaseTzInfo,
    *,
    now: datetime | None = None,
) -> bool:
    """`hhmm` vaqti bugun bo'lib o'tdimi tekshirish."""
    dt = parse_hhmm_to_dt(hhmm, base_date, tz)
    if dt is None:
        return False
    current = now or now_in_tz(tz)
    return current >= dt


#: Quiet hours diapazoni (mahalliy vaqt) — kechqurun eslatmalar o'chiriladi
QUIET_HOURS_START = 23  # 23:00
QUIET_HOURS_END = 5     # 05:00 ertasi


def is_in_quiet_hours(now_local: datetime) -> bool:
    """Mahalliy vaqt 23:00–05:00 oraligida bo'lsa True qaytaradi.

    Quiet hours kechasini bosib o'tadi (23 → 24 → 0 → 5).
    """
    h = now_local.hour
    if QUIET_HOURS_START <= QUIET_HOURS_END:
        # Bir kun ichida (masalan 23 <= h <= 5 noto'g'ri bo'lardi)
        return QUIET_HOURS_START <= h < QUIET_HOURS_END
    # Yarim kechani bosib o'tadi (default holat)
    return h >= QUIET_HOURS_START or h < QUIET_HOURS_END