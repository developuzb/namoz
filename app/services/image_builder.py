"""Namoz vaqtlari rasmini yasaydi (Pillow) — vertical card grid layout."""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.core.config import get_settings
from app.core.constants import ALL_PRAYERS
from app.core.logger import logger
from app.utils.time_utils import clean_hhmm

#: Default rasm o'lchami (1080x1080 — Telegram square optimal)
DEFAULT_SIZE: tuple[int, int] = (1080, 1080)

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

# ============== Rang palitrasi ==============
COLOR_BG_TOP = (12, 70, 40)             # to'q yashil (gradient yuqori)
COLOR_BG_BOTTOM = (8, 55, 32)           # gradient pastki
COLOR_CARD = (245, 238, 222)            # cream
COLOR_CARD_SHADOW = (5, 40, 22)         # card ostidagi soya
COLOR_TEXT_PRIMARY = (12, 70, 40)       # cardda asosiy matn
COLOR_TEXT_MUTED = (107, 122, 110)      # card prayer name
COLOR_TEXT_TIME = (24, 39, 32)          # katta vaqt
COLOR_TEXT_SUB = (12, 70, 40)           # jamoat satri
COLOR_HEADER = (255, 255, 255)          # header oq
COLOR_HEADER_DIM = (200, 215, 200)      # subtitle och
COLOR_DIVIDER = (180, 165, 130)         # cardda chiziqcha


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


def _draw_gradient_bg(img: Image.Image, top: tuple, bottom: tuple) -> None:
    """Vertikal gradient — yuqoridan pastga."""
    W, H = img.size
    overlay = Image.new("RGB", (1, H))
    for y in range(H):
        ratio = y / max(H - 1, 1)
        r = int(top[0] + (bottom[0] - top[0]) * ratio)
        g = int(top[1] + (bottom[1] - top[1]) * ratio)
        b = int(top[2] + (bottom[2] - top[2]) * ratio)
        overlay.putpixel((0, y), (r, g, b))
    overlay = overlay.resize((W, H))
    img.paste(overlay, (0, 0))


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

    Layout: vertical 3x2 card grid. Har card:
      - Yuqori chap: namoz nomi (kichik, muted)
      - Markaz: katta vaqt
      - Pastki: "Jamoat: HH:MM" (faqat Qashqadaryo regionlari uchun)
    """
    settings = get_settings()
    W, H = size

    home = _normalize_times(region_times)
    mosq = _normalize_times(masjid_times)

    has_mosq = any(mosq.get(p) for p in ALL_PRAYERS)
    if has_mosq:
        _apply_fallback(home, mosq)

    missing = [p for p in ALL_PRAYERS if not home.get(p)]
    if missing:
        logger.warning("{} uchun vaqt to'liq emas: {}", region_name, missing)

    # ============== Fon ==============
    img = Image.new("RGB", (W, H), COLOR_BG_TOP)
    _draw_gradient_bg(img, COLOR_BG_TOP, COLOR_BG_BOTTOM)
    d = ImageDraw.Draw(img)

    # ============== Fontlar ==============
    f_title = _load_font(FONT_FILES["title"], int(0.075 * H))
    _try_variant(f_title, "Bold")
    f_sub = _load_font(FONT_FILES["subtitle"], int(0.030 * H))
    f_card_name = _load_font(FONT_FILES["name"], int(0.030 * H))
    _try_variant(f_card_name, "SemiBold")
    f_card_time = _load_font(FONT_FILES["time"], int(0.082 * H))
    _try_variant(f_card_time, "Bold")
    f_card_sub = _load_font(FONT_FILES["subtitle"], int(0.026 * H))
    _try_variant(f_card_sub, "SemiBold")
    f_footer = _load_font(FONT_FILES["subtitle"], int(0.022 * H))

    # ============== Header ==============
    d.text(
        (W // 2, int(0.075 * H)),
        region_name.upper(),
        font=f_title, fill=COLOR_HEADER, anchor="mm",
    )
    d.text(
        (W // 2, int(0.135 * H)),
        f"{milodiy}",
        font=f_sub, fill=COLOR_HEADER, anchor="mm",
    )
    d.text(
        (W // 2, int(0.170 * H)),
        f"{hijriy}",
        font=f_sub, fill=COLOR_HEADER_DIM, anchor="mm",
    )

    # Header ostidagi nozik chiziq
    line_y = int(0.205 * H)
    line_x_pad = int(0.30 * W)
    d.line(
        (line_x_pad, line_y, W - line_x_pad, line_y),
        fill=COLOR_HEADER_DIM, width=2,
    )

    # ============== Cards 3x2 grid ==============
    card_margin_x = int(0.05 * W)
    card_gap_x = int(0.025 * W)
    card_gap_y = int(0.020 * H)
    grid_top = int(0.235 * H)
    grid_bottom = int(0.95 * H)

    grid_height = grid_bottom - grid_top
    card_w = (W - 2 * card_margin_x - card_gap_x) // 2
    card_h = (grid_height - 2 * card_gap_y) // 3
    radius = int(0.025 * W)

    for i, prayer in enumerate(ALL_PRAYERS):
        row, col = divmod(i, 2)
        x = card_margin_x + col * (card_w + card_gap_x)
        y = grid_top + row * (card_h + card_gap_y)
        x2 = x + card_w
        y2 = y + card_h

        # Soya (orqada)
        shadow_offset = 4
        d.rounded_rectangle(
            (x + shadow_offset, y + shadow_offset, x2 + shadow_offset, y2 + shadow_offset),
            radius=radius,
            fill=COLOR_CARD_SHADOW,
        )
        # Card
        d.rounded_rectangle((x, y, x2, y2), radius=radius, fill=COLOR_CARD)

        cx = (x + x2) // 2

        prayer_mosq = mosq.get(prayer)
        show_jamoat = has_mosq and bool(prayer_mosq)

        if show_jamoat:
            # 3 darajali kompozitsiya (nom, katta vaqt, jamoat)
            d.text(
                (cx, y + int(0.18 * card_h)),
                prayer.upper(),
                font=f_card_name, fill=COLOR_TEXT_MUTED, anchor="mm",
            )
            d.text(
                (cx, y + int(0.50 * card_h)),
                home.get(prayer) or EMPTY_MARK,
                font=f_card_time, fill=COLOR_TEXT_TIME, anchor="mm",
            )
            # Ajratuvchi chiziqcha
            div_y = y + int(0.72 * card_h)
            div_pad = int(card_w * 0.18)
            d.line(
                (x + div_pad, div_y, x2 - div_pad, div_y),
                fill=COLOR_DIVIDER, width=1,
            )
            d.text(
                (cx, y + int(0.86 * card_h)),
                f"Jamoat  {prayer_mosq}",
                font=f_card_sub, fill=COLOR_TEXT_SUB, anchor="mm",
            )
        else:
            # 2 darajali (nom + katta vaqt) — Quyosh kabi jamoatsiz namoz
            # yoki butunlay jamoatsiz region (Aladhan)
            d.text(
                (cx, y + int(0.30 * card_h)),
                prayer.upper(),
                font=f_card_name, fill=COLOR_TEXT_MUTED, anchor="mm",
            )
            d.text(
                (cx, y + int(0.65 * card_h)),
                home.get(prayer) or EMPTY_MARK,
                font=f_card_time, fill=COLOR_TEXT_TIME, anchor="mm",
            )

    # ============== Footer ==============
    attribution = (
        "islomapi.uz · O'zbekiston musulmonlari idorasi"
        if has_mosq
        else "Aladhan API · ISNA · Hanafi"
    )
    d.text(
        (W // 2, int(0.975 * H)),
        attribution,
        font=f_footer, fill=COLOR_HEADER_DIM, anchor="mm",
    )

    # ============== Saqlash ==============
    if out_filename:
        out_path = settings.images_dir / out_filename
    else:
        out_path = settings.images_dir / f"{_safe_filename(region_name)}.png"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    logger.debug("Rasm saqlandi: {}", out_path)
    return out_path


__all__ = ["make_prayer_image"]
