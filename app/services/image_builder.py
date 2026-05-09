"""Namoz vaqtlari rasmini yasaydi (Pillow). Eski image_maker.py portatsiyasi."""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.core.config import get_settings
from app.core.constants import ALL_PRAYERS
from app.core.logger import logger
from app.utils.time_utils import clean_hhmm

#: Default rasm o'lchami
DEFAULT_SIZE: tuple[int, int] = (1000, 1000)

#: Font fayllar (static/fonts/ ichida bo'lishi kerak)
FONT_FILES: dict[str, str] = {
    "title":    "Montserrat-VariableFont_wght.ttf",
    "subtitle": "Inter-VariableFont_opsz,wght.ttf",
    "header":   "SourceSans3-VariableFont_wght.ttf",
    "name":     "Nunito-VariableFont_wght.ttf",
    "time":     "Manrope-VariableFont_wght.ttf",
    "fallback": "NotoSans-VariableFont_wdth,wght.ttf",
}

#: Bo'sh vaqt ko'rsatkichi
EMPTY_MARK = "—"


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    return cleaned or "region"


def _load_font(filename: str, size: int) -> ImageFont.FreeTypeFont:
    settings = get_settings()
    path = settings.static_dir / "fonts" / filename
    if path.exists():
        try:
            return ImageFont.truetype(str(path), size)
        except OSError as e:
            logger.warning("Font yuklanmadi {}: {}", path.name, e)
    for cand in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(cand, size)
        except OSError:
            pass
    return ImageFont.load_default()  # type: ignore[return-value]


def _try_variant(font: ImageFont.FreeTypeFont, want: str) -> None:
    """Variable font da nomlangan instance ni yoqish (Bold/SemiBold)."""
    if not (
        hasattr(font, "get_variation_names")
        and hasattr(font, "set_variation_by_name")
    ):
        return
    try:
        names = font.get_variation_names()
        low = [n.lower() for n in names]
        for key in (want.lower(), "semibold", "bold", "regular"):
            if key in low:
                font.set_variation_by_name(names[low.index(key)])
                return
    except OSError as e:
        logger.debug("Font variant qo'yilmadi: {}", e)


def _normalize_times(d: dict[str, str]) -> dict[str, str]:
    """clean_hhmm bilan tozalash. None bo'lganlarni bo'sh string qilib qoldiradi."""
    return {k: (clean_hhmm(v) or "") for k, v in (d or {}).items()}


def _apply_fallback(home: dict[str, str], mosq: dict[str, str]) -> None:
    """Kirish vaqti bo'sh bo'lsa, masjid vaqtidan to'ldirish."""
    for prayer in ALL_PRAYERS:
        if not home.get(prayer) and mosq.get(prayer):
            home[prayer] = mosq[prayer]


def make_prayer_image(
    *,
    region_name: str,
    milodiy: str,
    hijriy: str,
    region_times: dict[str, str],
    masjid_times: dict[str, str],
    out_filename: str | None = None,
    size: tuple[int, int] = DEFAULT_SIZE,
) -> Path:
    """
    Rasm yasab `data/images/` ga saqlaydi va yo'lini qaytaradi.

    Args:
        region_name: hudud nomi (sarlavha)
        milodiy:     "9-may, 2026" ko'rinishida
        hijriy:      "23-shavvol, 1447-hijriy"
        region_times: provider dan kelgan kirish vaqtlari
        masjid_times: jamoat vaqtlari (bo'sh bo'lsa kirishdan to'ldiriladi)
        out_filename: faqat fayl nomi (data/images/ ichida); None bo'lsa slug.png
    """
    settings = get_settings()
    W, H = size

    home = _normalize_times(region_times)
    mosq = _normalize_times(masjid_times)

    # Masjid (jamoat) vaqtlari faqat Qashqadaryo regionlari uchun keladi.
    # Bo'sh bo'lsa — 2-ustunli layout (faqat Namoz + Kirish vaqti).
    has_mosq = any(mosq.get(p) for p in ALL_PRAYERS)
    if has_mosq:
        _apply_fallback(home, mosq)

    missing = [p for p in ALL_PRAYERS if not home.get(p)]
    if missing:
        logger.warning("{} uchun vaqt to'liq emas: {}", region_name, missing)

    img = Image.new("RGB", (W, H), (12, 70, 40))
    d = ImageDraw.Draw(img)

    f_title = _load_font(FONT_FILES["title"], int(0.075 * H))
    _try_variant(f_title, "Bold")
    f_sub = _load_font(FONT_FILES["subtitle"], int(0.042 * H))
    f_head = _load_font(FONT_FILES["header"], int(0.043 * H))
    _try_variant(f_head, "SemiBold")
    f_name = _load_font(FONT_FILES["name"], int(0.043 * H))
    _try_variant(f_name, "SemiBold")
    f_time = _load_font(FONT_FILES["time"], int(0.070 * H))
    _try_variant(f_time, "Bold")

    # Panel
    margin = int(0.08 * W)
    panel = (margin, int(0.25 * H), W - margin, H - margin)
    d.rounded_rectangle(panel, radius=int(0.03 * W), fill=(245, 238, 222))

    # Header
    d.text((W // 2, int(0.10 * H)), region_name.upper(),
           font=f_title, fill="white", anchor="mm")
    d.text((W // 2, int(0.17 * H)), f"{milodiy} | {hijriy}",
           font=f_sub, fill="white", anchor="mm")

    # Columns — has_mosq bo'lsa 3 ustun, aks holda 2 ustun (markazlangan)
    if has_mosq:
        x_name = int(0.20 * W)
        x_home = int(0.48 * W)
        x_mosq: int | None = int(0.80 * W)
    else:
        x_name = int(0.30 * W)
        x_home = int(0.70 * W)
        x_mosq = None
    y_head = int(0.315 * H)

    d.text((x_name, y_head), "Namoz", font=f_head, fill="black", anchor="mm")
    d.text((x_home, y_head), "Kirish vaqti", font=f_head, fill="black", anchor="mm")
    if x_mosq is not None:
        d.text((x_mosq, y_head), "Masjid (jamoat)", font=f_head, fill="black", anchor="mm")

    # Rows
    row_h = int(0.095 * H)
    start_y = int(0.405 * H)

    for i, prayer in enumerate(ALL_PRAYERS):
        cy = start_y + i * row_h
        d.text((x_name, cy), prayer, font=f_name, fill="black", anchor="mm")
        d.text((x_home, cy), home.get(prayer, "") or EMPTY_MARK,
               font=f_time, fill="black", anchor="mm")
        if x_mosq is not None:
            d.text((x_mosq, cy), mosq.get(prayer, "") or EMPTY_MARK,
                   font=f_time, fill="black", anchor="mm")

    if out_filename:
        out_path = settings.images_dir / out_filename
    else:
        out_path = settings.images_dir / f"{_safe_filename(region_name)}.png"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    logger.debug("Rasm saqlandi: {}", out_path)
    return out_path


__all__ = ["make_prayer_image"]
