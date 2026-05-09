"""Telegram caption (HTML) ni yasash — kanal va DM uchun."""
from __future__ import annotations

from datetime import date, datetime

from app.core.constants import (
    NAFL_GUIDE_URL,
    NAFL_ICONS,
    NAFL_PRAYERS,
)
from app.core.content import get_daily_ayah, get_daily_dua
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
    nafl_windows: dict[str, str],
    region_times: dict[str, str],
    masjid_times: dict[str, str],
    channel_link: str | None = None,
    attribution: str | None = None,
) -> str:
    """
    Kunlik post ning HTML caption ini yasaydi.

    Bo'limlar tartibi:
      1. Sarlavha (viloyat / tuman + sana + hafta kuni + hijriy)
      2. Nafl vaqtlari (Tahajjud, Ishroq, Zuho, Avvobiyn)
      3. Saharlik / Iftorlik
      4. Idora attribyutsiyasi
      5. Qur'on oyati (Niso 4:103)
      6. Nafl batafsil havolasi
      7. Kanal havolasi (bo'lsa)
    """
    dt = datetime(target_date.year, target_date.month, target_date.day)
    milodiy = format_milodiy_uz(dt)
    hafta = weekday_uz(dt)

    parent_safe = escape_html(parent_region_name)
    region_safe = escape_html(region_name)
    hijriy_safe = escape_html(hijriy)

    lines: list[str] = []

    # ========== 1. Sarlavha ==========
    if parent_safe and parent_safe != region_safe:
        lines.append(f"<b>{parent_safe} / {region_safe}</b>")
    else:
        lines.append(f"<b>{region_safe}</b>")
    lines.append(f"<b>{milodiy} ({hafta}) — {hijriy_safe}</b>")
    lines.append(f"📅 <i>Namoz vaqtlari: {milodiy} ({hafta}) kuni uchun</i>")

    # Juma kuni alohida tabrik (weekday() == 4 = Juma)
    if target_date.weekday() == 4:
        lines.append("")
        lines.append("🕌 <b>Bugun — muborak Juma kuni!</b>")
        lines.append(
            "<i>«Kunlarning eng yaxshisi — Juma kunidir.» (Muslim)</i>"
        )

    lines.append("")

    # ========== 2. Nafl vaqtlari ==========
    for prayer in NAFL_PRAYERS:
        window = nafl_windows.get(prayer)
        if not window:
            continue
        icon = NAFL_ICONS.get(prayer, "")
        lines.append(f"{icon} <b>{prayer}:</b> <code>{escape_html(window)}</code>")

    # ========== 3. Saharlik / Iftorlik ==========
    saharlik = (
        clean_hhmm(region_times.get("Bomdod"))
        or clean_hhmm(masjid_times.get("Bomdod"))
        or "—"
    )
    iftorlik = (
        clean_hhmm(region_times.get("Shom"))
        or clean_hhmm(masjid_times.get("Shom"))
        or "—"
    )
    lines.append("")
    lines.append(
        f"🍽 <b>Saharlik:</b> <code>{saharlik}</code>  |  "
        f"<b>Iftorlik:</b> <code>{iftorlik}</code>"
    )
    if attribution:
        lines.append(f"📚 <i>{escape_html(attribution)}</i>")

    # ========== 4. Qur'on oyati (har kuni boshqacha) ==========
    day_ord = target_date.toordinal()
    ayah = get_daily_ayah(day_ord)
    lines.append("")
    lines.append(f"📖 «{escape_html(ayah.uzbek)}»")
    lines.append(f"{ayah.arabic}")
    lines.append(f"<i>— {escape_html(ayah.ref)}</i>")

    # ========== 5. Kunning duosi (juft kunlarda — caption uzunligini chegaralash) ==========
    if day_ord % 2 == 0:
        dua = get_daily_dua(day_ord // 2)
        lines.append("")
        lines.append(f"🤲 <b>Kunning duosi:</b>")
        lines.append(f"{dua.arabic}")
        lines.append(f"<i>{escape_html(dua.uzbek)}</i>")

    # ========== 6. Nafl batafsil ==========
    lines.append("")
    lines.append(
        f'🧭 <a href="{NAFL_GUIDE_URL}">Nafl nima? Qanday o\'qiladi (batafsil)</a>'
    )

    # ========== 7. Kanal havolasi ==========
    link = normalize_channel_link(channel_link)
    if link:
        lines.append("")
        lines.append(f"🔗 {link}")

    return "\n".join(lines)


__all__ = ["build_post_caption"]
