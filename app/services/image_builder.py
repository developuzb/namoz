"""Namoz vaqtlari rasmini yasaydi (Pillow) — v2: 3D card grid bilan UX boost.

Yangi xususiyatlar:
- Real blurred drop shadow (haqiqiy chuqurlik)
- Card vertical gradient (yuqori ochroq, pastki to'qroq — yoritilgan effekti)
- Top highlight stroke (yorug'lik kart yuqorisiga tushganday)
- Keyingi namoz oltin halqa bilan ajratiladi + "Keyingi" badge
- Subtle yulduzli pattern fonda
"""
from __future__ import annotations

import math
import random
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.core.config import get_settings
from app.core.constants import ALL_PRAYERS
from app.core.logger import logger
from app.utils.time_utils import clean_hhmm

#: Default rasm o'lchami
DEFAULT_SIZE: tuple[int, int] = (1080, 1080)

FONT_FILES: dict[str, str] = {
    "title":    "Montserrat-VariableFont_wght.ttf",
    "subtitle": "Inter-VariableFont_opsz,wght.ttf",
    "header":   "SourceSans3-VariableFont_wght.ttf",
    "name":     "Nunito-VariableFont_wght.ttf",
    "time":     "Manrope-VariableFont_wght.ttf",
    "fallback": "NotoSans-VariableFont_wdth,wght.ttf",
}

EMPTY_MARK = "—"

# ============== Rang palitrasi ==============
COLOR_BG_TOP = (14, 75, 44)              # to'q yashil yuqori
COLOR_BG_BOTTOM = (6, 45, 26)            # to'q yashil pastki
COLOR_CARD_TOP = (250, 244, 230)         # cream yuqori (yoritilgan)
COLOR_CARD_BOTTOM = (235, 225, 205)      # cream pastki (soya)
COLOR_CARD_HIGHLIGHT_TOP = (255, 250, 240)  # current card yuqori — yorqinroq
COLOR_CARD_HIGHLIGHT_BOTTOM = (240, 228, 200)
COLOR_TEXT_PRIMARY = (12, 70, 40)
COLOR_TEXT_MUTED = (107, 122, 110)
COLOR_TEXT_TIME = (24, 39, 32)
COLOR_TEXT_SUB = (12, 70, 40)
COLOR_HEADER = (255, 255, 255)
COLOR_HEADER_DIM = (190, 215, 195)
COLOR_DIVIDER = (180, 165, 130)
COLOR_GOLD = (212, 168, 95)              # current card oltin halqa
COLOR_GOLD_GLOW = (242, 198, 125)        # yorqinroq oltin
COLOR_TOP_HIGHLIGHT = (255, 252, 245, 180)  # card yuqorisidagi yorug'lik stroke
COLOR_STAR = (255, 255, 255, 18)         # juda och oq — fon yulduzlari


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
    return {k: (clean_hhmm(v) or "") for k, v in (d or {}).items()}


def _apply_fallback(home: dict[str, str], mosq: dict[str, str]) -> None:
    for prayer in ALL_PRAYERS:
        if not home.get(prayer) and mosq.get(prayer):
            home[prayer] = mosq[prayer]


# ============== Pastki darajadagi grafik yordamchilar ==============

def _make_vertical_gradient(
    w: int, h: int, top: tuple[int, int, int], bottom: tuple[int, int, int]
) -> Image.Image:
    """Vertikal gradient (yuqori → pastki). Optimallashtirilgan."""
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        ratio = y / max(h - 1, 1)
        r = int(top[0] + (bottom[0] - top[0]) * ratio)
        g = int(top[1] + (bottom[1] - top[1]) * ratio)
        b = int(top[2] + (bottom[2] - top[2]) * ratio)
        grad.putpixel((0, y), (r, g, b))
    return grad.resize((w, h))


def _make_card(
    w: int,
    h: int,
    radius: int,
    top_color: tuple[int, int, int],
    bottom_color: tuple[int, int, int],
    *,
    top_highlight: bool = True,
) -> Image.Image:
    """Yumshoq gradient bilan rounded rect card yasaydi (RGBA).

    Top highlight: faqat YUQORI burchak atrofida ingichka chiziq.
    Pastki burchaklar uchun chiziq yo'q — yorug'lik yuqoridan tushadi.
    """
    # Mask: rounded rect (full alpha)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, w, h), radius=radius, fill=255,
    )
    # Gradient body
    grad = _make_vertical_gradient(w, h, top_color, bottom_color)
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    card.paste(grad, (0, 0), mask)

    # Top highlight: yarim aylana chiziq yuqori burchakda (boshidan oxirigacha)
    if top_highlight:
        d = ImageDraw.Draw(card, "RGBA")
        # Yuqori chap burchak yoyi
        d.arc(
            (1, 1, 2 * radius, 2 * radius),
            start=180, end=270,
            fill=COLOR_TOP_HIGHLIGHT, width=2,
        )
        # Yuqori chiziq (gorizontal)
        d.line(
            (radius, 1, w - radius, 1),
            fill=COLOR_TOP_HIGHLIGHT, width=2,
        )
        # Yuqori o'ng burchak yoyi
        d.arc(
            (w - 2 * radius - 1, 1, w - 2, 2 * radius),
            start=270, end=360,
            fill=COLOR_TOP_HIGHLIGHT, width=2,
        )

    return card


def _make_shadow(
    w: int, h: int, radius: int, *, blur: int = 18, opacity: int = 130
) -> Image.Image:
    """Soft drop shadow — Gaussian blur."""
    pad = blur * 2
    canvas = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).rounded_rectangle(
        (pad, pad, w + pad, h + pad),
        radius=radius, fill=(0, 0, 0, opacity),
    )
    return canvas.filter(ImageFilter.GaussianBlur(blur))


def _draw_gold_ring(
    img: Image.Image, x: int, y: int, x2: int, y2: int, radius: int
) -> None:
    """Card atrofiga oltin glow + chiziqli halqa qo'shadi."""
    # Tashqi glow (blur bilan)
    pad = 12
    glow = Image.new("RGBA", (img.size[0], img.size[1]), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle(
        (x - pad, y - pad, x2 + pad, y2 + pad),
        radius=radius + pad,
        outline=COLOR_GOLD_GLOW + (160,),
        width=8,
    )
    glow = glow.filter(ImageFilter.GaussianBlur(8))
    img.alpha_composite(glow)

    # Aniq halqa
    ring = Image.new("RGBA", (img.size[0], img.size[1]), (0, 0, 0, 0))
    ImageDraw.Draw(ring).rounded_rectangle(
        (x - 2, y - 2, x2 + 2, y2 + 2),
        radius=radius + 2,
        outline=COLOR_GOLD + (255,),
        width=4,
    )
    img.alpha_composite(ring)


def _draw_star_pattern(img: Image.Image, count: int = 50) -> None:
    """Fon ustiga juda och yulduzlar — atmosfera uchun."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    rng = random.Random(42)  # deterministik joylashuv
    for _ in range(count):
        x = rng.randint(0, img.size[0])
        y = rng.randint(0, int(img.size[1] * 0.22))  # yuqori 22% da
        size = rng.choice([1, 2, 2, 3])
        ImageDraw.Draw(layer).ellipse(
            (x - size, y - size, x + size, y + size),
            fill=COLOR_STAR,
        )
    img.alpha_composite(layer)


# ============== Asosiy generator ==============

def make_prayer_image(
    *,
    region_name: str,
    milodiy: str,
    hijriy: str,
    region_times: dict[str, str],
    masjid_times: dict[str, str],
    out_filename: str | None = None,
    size: tuple[int, int] = DEFAULT_SIZE,
    highlight_prayer: str | None = None,
) -> Path:
    """
    3D card grid layout bilan rasm yasaydi.

    Args:
        highlight_prayer: oltin halqa bilan belgilanadigan namoz (masalan keyingisi)
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
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bg = _make_vertical_gradient(W, H, COLOR_BG_TOP, COLOR_BG_BOTTOM).convert("RGBA")
    img.paste(bg, (0, 0))
    _draw_star_pattern(img, count=60)
    d = ImageDraw.Draw(img)

    # ============== Fontlar ==============
    f_title = _load_font(FONT_FILES["title"], int(0.072 * H))
    _try_variant(f_title, "Bold")
    f_sub = _load_font(FONT_FILES["subtitle"], int(0.030 * H))
    f_card_name = _load_font(FONT_FILES["name"], int(0.030 * H))
    _try_variant(f_card_name, "SemiBold")
    f_card_time = _load_font(FONT_FILES["time"], int(0.084 * H))
    _try_variant(f_card_time, "Bold")
    f_card_sub = _load_font(FONT_FILES["subtitle"], int(0.026 * H))
    _try_variant(f_card_sub, "SemiBold")
    f_badge = _load_font(FONT_FILES["subtitle"], int(0.022 * H))
    _try_variant(f_badge, "Bold")
    f_footer = _load_font(FONT_FILES["subtitle"], int(0.022 * H))

    # ============== Header ==============
    d.text(
        (W // 2, int(0.075 * H)),
        region_name.upper(),
        font=f_title, fill=COLOR_HEADER, anchor="mm",
    )
    d.text(
        (W // 2, int(0.135 * H)),
        milodiy,
        font=f_sub, fill=COLOR_HEADER, anchor="mm",
    )
    d.text(
        (W // 2, int(0.170 * H)),
        hijriy,
        font=f_sub, fill=COLOR_HEADER_DIM, anchor="mm",
    )

    line_y = int(0.205 * H)
    line_x_pad = int(0.32 * W)
    d.line(
        (line_x_pad, line_y, W - line_x_pad, line_y),
        fill=COLOR_HEADER_DIM, width=2,
    )

    # ============== Cards 3x2 grid ==============
    card_margin_x = int(0.05 * W)
    card_gap_x = int(0.025 * W)
    card_gap_y = int(0.022 * H)
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

        is_highlighted = (highlight_prayer == prayer)

        # 1) Drop shadow
        shadow = _make_shadow(card_w, card_h, radius, blur=20, opacity=140)
        img.alpha_composite(shadow, (x - 36, y - 32))

        # 2) Card body (gradient + top highlight)
        if is_highlighted:
            card = _make_card(
                card_w, card_h, radius,
                COLOR_CARD_HIGHLIGHT_TOP, COLOR_CARD_HIGHLIGHT_BOTTOM,
                top_highlight=True,
            )
        else:
            card = _make_card(
                card_w, card_h, radius,
                COLOR_CARD_TOP, COLOR_CARD_BOTTOM,
                top_highlight=True,
            )
        img.alpha_composite(card, (x, y))

        # 3) Oltin halqa (highlighted bo'lsa)
        if is_highlighted:
            _draw_gold_ring(img, x, y, x2, y2, radius)

        # 4) Card matnlari
        cx = (x + x2) // 2
        prayer_mosq = mosq.get(prayer)
        show_jamoat = has_mosq and bool(prayer_mosq)

        if show_jamoat:
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

        # 5) Highlighted card uchun "KEYINGI" badge (yuqori-o'ng burchakda)
        if is_highlighted:
            badge_text = "KEYINGI"
            bbox = d.textbbox((0, 0), badge_text, font=f_badge)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            pad_x, pad_y = int(card_w * 0.025), int(card_h * 0.04)
            bx = x2 - tw - pad_x * 2 - 8
            by = y + 8
            d.rounded_rectangle(
                (bx, by, bx + tw + pad_x * 2, by + th + pad_y * 2),
                radius=int(th * 0.7),
                fill=COLOR_GOLD,
            )
            d.text(
                (bx + pad_x, by + pad_y - 2),
                badge_text,
                font=f_badge, fill=(255, 255, 255),
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
    img.convert("RGB").save(out_path)
    logger.debug("Rasm saqlandi: {}", out_path)
    return out_path


__all__ = ["make_prayer_image"]
