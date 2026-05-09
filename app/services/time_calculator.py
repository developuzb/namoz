"""Nafl namozlari oraliqlarini va joriy nafl statusini hisoblash."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytz

from app.core.constants import NAFL_PRAYERS
from app.core.logger import logger
from app.utils.time_utils import parse_hhmm_to_dt


def _first_dt(
    target_date: date,
    tz: pytz.BaseTzInfo,
    *sources: dict[str, str],
    key: str,
) -> datetime | None:
    """Bir nechta dict dan birinchi to'ldirilgan vaqtni datetime ga aylantiradi."""
    for src in sources:
        if not src:
            continue
        value = src.get(key)
        if value:
            dt = parse_hhmm_to_dt(value, target_date, tz)
            if dt is not None:
                return dt
    return None


def calculate_nafl_windows(
    *,
    region_times: dict[str, str],
    masjid_times: dict[str, str],
    target_date: date,
    tz: pytz.BaseTzInfo,
) -> dict[str, str]:
    """
    Nafl vaqt oraliqlarini hisoblash.

    Returns:
        {nafl: "HH:MM — HH:MM"} — agar hisoblay olmasa kalit yo'q.
    """
    bomdod = _first_dt(target_date, tz, region_times, masjid_times, key="Bomdod")
    quyosh = _first_dt(target_date, tz, region_times, key="Quyosh")
    peshin = _first_dt(target_date, tz, region_times, masjid_times, key="Peshin")
    shom = _first_dt(target_date, tz, region_times, masjid_times, key="Shom")
    xufton = _first_dt(target_date, tz, region_times, masjid_times, key="Xufton")

    out: dict[str, str] = {}

    # ----- Tahajjud — kechaning oxirgi 1/3 (Xuftondan ertangi Bomdodgacha) -----
    if xufton and bomdod:
        bomdod_next = bomdod + timedelta(days=1)
        night = bomdod_next - xufton
        if night.total_seconds() > 0:
            start = bomdod_next - night / 3 + timedelta(minutes=5)
            end = bomdod_next - timedelta(minutes=5)
            if end > start:
                out["Tahajjud"] = f"{start:%H:%M} — {end:%H:%M}"

    # ----- Ishroq — quyoshdan 15-60 daqiqa keyin -----
    if quyosh:
        start = quyosh + timedelta(minutes=15)
        end = quyosh + timedelta(minutes=60)
        out["Ishroq"] = f"{start:%H:%M} — {end:%H:%M}"

    # ----- Zuho — quyoshdan 2 soat keyin Peshindan 30 daq oldin -----
    if quyosh and peshin:
        start = quyosh + timedelta(minutes=120)
        end = peshin - timedelta(minutes=30)
        if end > start:
            out["Zuho"] = f"{start:%H:%M} — {end:%H:%M}"

    # ----- Avvobiyn — Shomdan Xuftongacha -----
    if shom and xufton and xufton > shom:
        out["Avvobiyn"] = f"{shom:%H:%M} — {xufton:%H:%M}"

    logger.debug("Nafl oraliqlari hisoblandi: {}", list(out.keys()))
    return out


def get_current_nafl_status(
    *,
    region_times: dict[str, str],
    target_date: date,
    tz: pytz.BaseTzInfo,
    now: datetime | None = None,
) -> str:
    """
    Hozirgi vaqtga ko'ra qaysi nafl o'qish mumkinligini foydalanuvchiga bayon qiladi.

    Telegram inline-tugma bosilganda alert sifatida ko'rsatiladi.
    """
    if now is None:
        now = datetime.now(tz)

    def _get(key: str) -> datetime | None:
        return _first_dt(target_date, tz, region_times, key=key)

    bomdod = _get("Bomdod")
    quyosh = _get("Quyosh")
    peshin = _get("Peshin")
    asr = _get("Asr")
    shom = _get("Shom")
    xufton = _get("Xufton")

    if bomdod and quyosh and bomdod <= now < quyosh:
        return "❌ Hozir nafl o'qilmaydi\n(Bomdoddan quyosh chiqquncha)"

    if quyosh and peshin and quyosh + timedelta(minutes=15) <= now < peshin:
        return "☀️ Ishroq / Zuho o'qish mumkin"

    if peshin and asr and peshin <= now < asr:
        return "🌤 Nafl o'qish mumkin\n(Peshin → Asr oralig'i)"

    if asr and shom and asr <= now < shom:
        return "❌ Hozir nafl o'qilmaydi\n(Asrdan Shomgacha)"

    if shom and xufton and shom <= now < xufton:
        return "🌇 Avvobiyn o'qish mumkin"

    if xufton and now >= xufton:
        return "🌙 Nafl o'qish mumkin\n(Tahajjud — tun oxirida)"

    return "ℹ️ Nafl holati aniqlanmadi"


__all__ = [
    "NAFL_PRAYERS",
    "calculate_nafl_windows",
    "get_current_nafl_status",
]
