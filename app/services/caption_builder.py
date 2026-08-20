"""Telegram caption (HTML) ni yasash — kanal va DM uchun."""
from __future__ import annotations

from datetime import date, datetime

from app.core.content import get_daily_ayah
from app.services.holidays import get_holiday, get_ramadan_day
from app.utils.text_utils import (
    escape_html,
    format_milodiy_uz,
    normalize_channel_link,
    weekday_uz,
)
from app.utils.time_utils import clean_hhmm


def build_post_caption(
    *,
    parent_region_name: str,
    region_name: str,
    target_date: date,
    hijriy: str,
    region_times: dict[str, str],
    masjid_times: dict[str, str],
    channel_link: str | None = None,
    attribution: str | None = None,
    tahajjud: str | None = None,
) -> str:
    """Kunlik post HTML caption ini yasaydi.

    Tartib (yuqoridan pastga):
      1. Kanal havolasi (bo'lsa) + region + sana + hijriy — barchasi yuqorida
      2. Ramazon / hijriy bayram / Juma tabriklari (agar bo'lsa)
      3. Saharlik / Iftorlik
      4. Qur'on oyati
    """
    dt = datetime(target_date.year, target_date.month, target_date.day)
    milodiy = format_milodiy_uz(dt)
    hafta = weekday_uz(dt)

    parent_safe = escape_html(parent_region_name)
    region_safe = escape_html(region_name)
    hijriy_safe = escape_html(hijriy)

    lines: list[str] = []

    # ========== 1. Yuqori meta blok ==========
    link = normalize_channel_link(channel_link)
    if link:
        lines.append(f"🔗 {link}")

    if parent_safe and parent_safe != region_safe:
        lines.append(f"📍 <b>{parent_safe} / {region_safe}</b>")
    else:
        lines.append(f"📍 <b>{region_safe}</b>")
    lines.append(f"🗓 <b>{milodiy} ({hafta})</b>")
    lines.append(f"🕌 <i>{hijriy_safe}</i>")

    # Ramazon kuni badge
    ramadan_day = get_ramadan_day(target_date)
    if ramadan_day:
        lines.append(f"🌙 <b>RAMAZON — {ramadan_day}-kun</b>")

    # ========== 2. Hijriy bayram / Juma tabriklari ==========
    holiday = get_holiday(target_date)
    if holiday:
        lines.append("")
        lines.append(holiday.greeting)

    if target_date.weekday() == 4 and (not holiday or holiday.key != "eid_al_fitr"):
        lines.append("")
        lines.append("🕌 <b>Bugun — muborak Juma kuni!</b>")
        lines.append(
            "<i>«Kunlarning eng yaxshisi — Juma kunidir.» (Muslim)</i>"
        )
        lines.append(
            "🤲 <i>Sadaqa qilish, surai Kahf o'qish va salavot aytishni unutmang.</i>"
        )

    # ========== 3. Saharlik / Iftorlik ==========
    # Saharlik = Bomdod (Fajr) vaqti — islomapi tong_saharlik bilan bir xil.
    # Iftorlik = Shom (Mag'rib) vaqti.
    saharlik = (
        clean_hhmm(region_times.get("Bomdod"))
        or "—"
    )
    iftorlik = (
        clean_hhmm(region_times.get("Shom"))
        or "—"
    )
    lines.append("")
    lines.append(f"🌙 <b>Saharlik:</b> <code>{saharlik}</code>")
    lines.append(f"🌇 <b>Iftorlik:</b> <code>{iftorlik}</code>")
    # Tahajjud — kechaning oxirgi 1/3 qismi (Xuftondan ertangi Bomdodgacha)
    if tahajjud:
        lines.append(f"🌌 <b>Tahajjud:</b> <code>{escape_html(tahajjud)}</code>")

    # ========== 4. Qur'on oyati ==========
    day_ord = target_date.toordinal()
    ayah = get_daily_ayah(day_ord)
    lines.append("")
    lines.append(f"📖 «{escape_html(ayah.uzbek)}»")
    lines.append(f"{ayah.arabic}")
    lines.append(f"<i>— {escape_html(ayah.ref)}</i>")

    # `attribution` argumenti endi ishlatilmaydi (manba/uslub olib tashlandi),
    # lekin imzosini saqlaymiz — eski kod chaqiruvlari sinmasin.
    _ = attribution
    return "\n".join(lines)


__all__ = ["build_post_caption"]
