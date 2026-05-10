"""Oylik kalendar — 1 oydagi har kun uchun namoz vaqtlari rasmi."""
from __future__ import annotations

import calendar
import re
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.core.config import get_settings
from app.core.constants import ALL_PRAYERS, MONTHS_UZ, WEEKDAYS_UZ
from app.core.exceptions import ProviderError
from app.core.logger import logger
from app.db.models.region import Region
from app.services.registry import get_prayer_service


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    return cleaned or "calendar"


def _load_font(filename: str, size: int) -> ImageFont.FreeTypeFont:
    settings = get_settings()
    path = settings.static_dir / "fonts" / filename
    if path.exists():
        try:
            return ImageFont.truetype(str(path), size)
        except OSError:
            pass
    return ImageFont.load_default()  # type: ignore[return-value]


async def get_month_data(
    region: Region, year: int, month: int
) -> dict[int, dict[str, str]]:
    """Oyning har kuni uchun namoz vaqtlari.

    1. Agar region.provider_name set bo'lsa → islomapi monthly endpoint (bitta call)
    2. Aks holda → har kun uchun PrayerService chain (sekinroq, lekin universal)
    """
    service = get_prayer_service()

    # Tezroq yo'l — islomapi monthly
    if region.provider_name:
        try:
            return await service.islomapi.fetch_month_raw(
                region.provider_name, year, month,
            )
        except ProviderError as e:
            logger.debug("islomapi monthly fail for {}: {}", region.name, e)

    # Universal yo'l — har kun alohida (kechroq lekin har provider'da ishlaydi)
    days_in_month = calendar.monthrange(year, month)[1]
    out: dict[int, dict[str, str]] = {}
    for day in range(1, days_in_month + 1):
        try:
            pt = await service.fetch_for_region(region, date(year, month, day))
            out[day] = pt.times
        except ProviderError as e:
            logger.debug(
                "Day {} fetch fail for {}: {}", day, region.name, e,
            )
            continue
    return out


def make_month_calendar_image(
    *,
    region_name: str,
    year: int,
    month: int,
    days_data: dict[int, dict[str, str]],
    out_filename: str | None = None,
) -> Path:
    """Oylik kalendar PNG ni yasaydi (1080x1500)."""
    settings = get_settings()
    W, H = 1080, 1500

    days_in_month = calendar.monthrange(year, month)[1]
    first_weekday = date(year, month, 1).weekday()  # Mon=0..Sun=6

    # ============== Fon ==============
    img = Image.new("RGB", (W, H), (252, 245, 230))
    d = ImageDraw.Draw(img)

    # ============== Header ==============
    f_title = _load_font("Montserrat-VariableFont_wght.ttf", 56)
    d.text(
        (W // 2, 65), region_name.upper(),
        font=f_title, fill=(50, 30, 70), anchor="mm",
    )
    f_sub = _load_font("Inter-VariableFont_opsz,wght.ttf", 36)
    d.text(
        (W // 2, 130),
        f"{MONTHS_UZ[month].upper()} {year}",
        font=f_sub, fill=(100, 90, 110), anchor="mm",
    )

    # Oltin chiziqcha
    line_y = 175
    line_pad = int(W * 0.30)
    d.line((line_pad, line_y, W - line_pad, line_y), fill=(212, 165, 95), width=3)

    # ============== Grid header (ustun nomlari) ==============
    cols = ["Kun", "Bomdod", "Quyosh", "Peshin", "Asr", "Shom", "Xufton"]
    col_x = [70, 220, 350, 480, 610, 740, 880]  # markaz X koordinatalari

    grid_top = 220
    f_head = _load_font("SourceSans3-VariableFont_wght.ttf", 26)
    for col, x in zip(cols, col_x):
        d.text((x, grid_top), col, font=f_head, fill=(80, 65, 95), anchor="mm")

    # Header ostida chiziq
    d.line(
        (40, grid_top + 25, W - 40, grid_top + 25),
        fill=(200, 175, 195), width=2,
    )

    # ============== Rows (kunlar) ==============
    f_cell = _load_font("Manrope-VariableFont_wght.ttf", 22)
    f_day = _load_font("Manrope-VariableFont_wght.ttf", 24)
    row_h = (H - grid_top - 100) // (days_in_month + 1)
    rows_top = grid_top + 50

    for day in range(1, days_in_month + 1):
        y = rows_top + (day - 1) * row_h
        # Juma kunlarini fonini biroz ajratamiz
        weekday = (first_weekday + day - 1) % 7  # Mon=0..Sun=6, Juma=4
        if weekday == 4:  # Friday
            d.rectangle(
                (40, y - row_h // 2 + 4, W - 40, y + row_h // 2 - 4),
                fill=(255, 245, 220),
            )

        # Kun raqami
        d.text(
            (col_x[0], y),
            f"{day} {WEEKDAYS_UZ[weekday][:3]}",
            font=f_day, fill=(50, 30, 70), anchor="mm",
        )

        # Vaqtlar
        times = days_data.get(day, {})
        for i, prayer in enumerate(ALL_PRAYERS):
            t = times.get(prayer, "—")
            color = (28, 30, 50) if t != "—" else (180, 175, 175)
            d.text(
                (col_x[i + 1], y), t,
                font=f_cell, fill=color, anchor="mm",
            )

    # ============== Footer ==============
    f_footer = _load_font("Inter-VariableFont_opsz,wght.ttf", 20)
    foot_y = H - 35
    d.text(
        (W // 2, foot_y),
        f"Jami {len(days_data)}/{days_in_month} kun · taqvim_bot",
        font=f_footer, fill=(100, 90, 110), anchor="mm",
    )

    if out_filename:
        out_path = settings.images_dir / out_filename
    else:
        out_path = settings.images_dir / (
            f"calendar_{_safe_filename(region_name)}_{year}{month:02d}.png"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, optimize=True, quality=92)
    logger.debug("Monthly calendar saqlandi: {}", out_path)
    return out_path


__all__ = ["get_month_data", "make_month_calendar_image"]
