"""Namoz vaqtlari rasmini yasaydi (Pillow) — v4: premium quality.

Yangiliklar v3 ga nisbatan:
- 3-stop sunset gradient (yorqin-mayin)
- Multi-layer drop shadows (tight + diffuse)
- Card subtle gradient (oq → ozgina cream)
- Kattaroq emoji (~50% card balandlikdan)
- Kattaroq time font (xizmat ko'rsatish — eng muhim ma'lumot)
- Header: decorative chiziqli ornament shahar nomi atrofida
- Footer: oltin chiziqcha + attribyutsiya
- Highlighted card: ikki qatlamli oltin glow
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.core.config import get_settings
from app.core.constants import ALL_PRAYERS
from app.core.logger import logger
from app.utils.time_utils import clean_hhmm

DEFAULT_SIZE: tuple[int, int] = (1080, 1080)

FONT_FILES: dict[str, str] = {
    "title":    "Montserrat-VariableFont_wght.ttf",
    "subtitle": "Inter-VariableFont_opsz,wght.ttf",
    "header":   "SourceSans3-VariableFont_wght.ttf",
    "name":     "Nunito-VariableFont_wght.ttf",
    "time":     "Manrope-VariableFont_wght.ttf",
    "fallback": "NotoSans-VariableFont_wdth,wght.ttf",
}

EMOJI_FILES: dict[str, str] = {
    "Bomdod":   "sunrise.png",
    "Quyosh":   "sunrise_mt.png",
    "Peshin":   "sun_face.png",
    "Asr":      "sun_cloud.png",
    "Shom":     "sunset.png",
    "Xufton":   "moon.png",
}

EMPTY_MARK = "—"

# ============== 3-stop sunset gradient (premium yorqin) ==============
COLOR_BG_TOP = (255, 198, 196)        # coral pink (yuqori)
COLOR_BG_MID = (255, 225, 184)        # warm peach (o'rta)
COLOR_BG_BOTTOM = (228, 207, 245)     # soft lavender (pastki)

# Cards
COLOR_CARD_TOP = (255, 255, 255)      # toza oq
COLOR_CARD_BOTTOM = (250, 248, 244)   # juda och cream — gradient pastki
COLOR_CARD_HIGHLIGHT_TOP = (255, 252, 240)
COLOR_CARD_HIGHLIGHT_BOTTOM = (252, 245, 220)

# Per-prayer accent (top stripe)
COLOR_ACCENT: dict[str, tuple[int, int, int]] = {
    "Bomdod":  (255, 121, 84),
    "Quyosh":  (255, 167, 38),
    "Peshin":  (38, 198, 218),
    "Asr":     (255, 152, 0),
    "Shom":    (244, 81, 108),
    "Xufton":  (126, 87, 194),
}

# Text
COLOR_TEXT_NAME = (90, 80, 100)
COLOR_TEXT_TIME = (28, 30, 50)
COLOR_TEXT_JAMOAT = (90, 110, 90)
COLOR_DIVIDER = (235, 225, 220)

# Header
COLOR_HEADER_TEXT = (50, 30, 70)
COLOR_HEADER_DIM = (100, 90, 110)
COLOR_HEADER_LINE = (200, 175, 195)
COLOR_HEADER_DOT = (212, 165, 110)

# Highlighted (KEYINGI)
COLOR_GOLD = (212, 165, 95)
COLOR_GOLD_GLOW_OUT = (255, 215, 130)
COLOR_GOLD_GLOW_IN = (255, 230, 170)


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


def _make_3stop_gradient(
    w: int, h: int,
    top: tuple[int, int, int],
    mid: tuple[int, int, int],
    bottom: tuple[int, int, int],
) -> Image.Image:
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        ratio = y / max(h - 1, 1)
        if ratio < 0.5:
            t = ratio * 2  # 0..1
            r = int(top[0] + (mid[0] - top[0]) * t)
            g = int(top[1] + (mid[1] - top[1]) * t)
            b = int(top[2] + (mid[2] - top[2]) * t)
        else:
            t = (ratio - 0.5) * 2
            r = int(mid[0] + (bottom[0] - mid[0]) * t)
            g = int(mid[1] + (bottom[1] - mid[1]) * t)
            b = int(mid[2] + (bottom[2] - mid[2]) * t)
        grad.putpixel((0, y), (r, g, b))
    return grad.resize((w, h))


def _make_card(
    w: int, h: int, radius: int,
    top_color: tuple[int, int, int],
    bottom_color: tuple[int, int, int],
) -> Image.Image:
    """Card with subtle vertical gradient (top lighter)."""
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, w, h), radius=radius, fill=255,
    )
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        ratio = y / max(h - 1, 1)
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        grad.putpixel((0, y), (r, g, b))
    grad = grad.resize((w, h))
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    card.paste(grad, (0, 0), mask)
    return card


def _make_shadow_layer(
    w: int, h: int, radius: int, *, blur: int, opacity: int
) -> Image.Image:
    pad = blur * 2
    canvas = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).rounded_rectangle(
        (pad, pad, w + pad, h + pad),
        radius=radius, fill=(0, 0, 0, opacity),
    )
    return canvas.filter(ImageFilter.GaussianBlur(blur))


def _draw_multi_shadow(
    img: Image.Image, x: int, y: int, w: int, h: int, radius: int
) -> None:
    """Tight + diffuse shadow combined for premium depth."""
    # Diffuse (large blur, light)
    diffuse = _make_shadow_layer(w, h, radius, blur=28, opacity=40)
    img.alpha_composite(diffuse, (x - 56, y - 48))
    # Tight (small blur, slightly darker)
    tight = _make_shadow_layer(w, h, radius, blur=10, opacity=50)
    img.alpha_composite(tight, (x - 20, y - 14))


def _draw_gold_glow_double(
    img: Image.Image, x: int, y: int, x2: int, y2: int, radius: int
) -> None:
    """Two-layer gold glow + ring for highlighted card."""
    # Tashqi diffuse glow
    pad = 22
    glow_outer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow_outer).rounded_rectangle(
        (x - pad, y - pad, x2 + pad, y2 + pad),
        radius=radius + pad,
        outline=COLOR_GOLD_GLOW_OUT + (130,),
        width=14,
    )
    glow_outer = glow_outer.filter(ImageFilter.GaussianBlur(14))
    img.alpha_composite(glow_outer)

    # O'rta yorqin glow
    pad2 = 8
    glow_mid = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow_mid).rounded_rectangle(
        (x - pad2, y - pad2, x2 + pad2, y2 + pad2),
        radius=radius + pad2,
        outline=COLOR_GOLD_GLOW_IN + (200,),
        width=8,
    )
    glow_mid = glow_mid.filter(ImageFilter.GaussianBlur(5))
    img.alpha_composite(glow_mid)

    # Aniq oltin halqa
    ring = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ring).rounded_rectangle(
        (x - 3, y - 3, x2 + 3, y2 + 3),
        radius=radius + 3,
        outline=COLOR_GOLD + (255,),
        width=4,
    )
    img.alpha_composite(ring)


def _load_emoji(filename: str, target_size: int) -> Image.Image | None:
    settings = get_settings()
    path = settings.static_dir / "emojis" / filename
    if not path.exists():
        return None
    try:
        em = Image.open(path).convert("RGBA")
        em.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)
        return em
    except (OSError, ValueError):
        return None


def _draw_top_accent(
    img: Image.Image, x: int, y: int, w: int, h: int, radius: int,
    color: tuple[int, int, int],
) -> None:
    stripe_h = 6
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, w, h), radius=radius, fill=255,
    )
    body = Image.new("RGB", (w, stripe_h), color)
    layer.paste(body, (0, 0))
    top_mask = Image.new("L", (w, h), 0)
    top_mask.paste(mask.crop((0, 0, w, stripe_h)), (0, 0))
    layer.putalpha(top_mask)
    img.alpha_composite(layer, (x, y))


def _draw_header_ornament(
    d: ImageDraw.ImageDraw, cx: int, cy: int, total_w: int
) -> None:
    """Shahar nomi atrofida ikki tomonlama dekorativ chiziq + nuqta.

    Rasm:    ── ●  shahar  ● ──
    """
    line_len = 80
    gap = 18
    dot_r = 4
    # Chap chiziq + nuqta
    left_end = cx - total_w // 2 - gap
    left_start = left_end - line_len
    d.line((left_start, cy, left_end, cy), fill=COLOR_HEADER_LINE, width=2)
    d.ellipse(
        (left_end + 4 - dot_r, cy - dot_r, left_end + 4 + dot_r, cy + dot_r),
        fill=COLOR_HEADER_DOT,
    )
    # O'ng chiziq + nuqta
    right_start = cx + total_w // 2 + gap
    right_end = right_start + line_len
    d.ellipse(
        (right_start - 4 - dot_r, cy - dot_r, right_start - 4 + dot_r, cy + dot_r),
        fill=COLOR_HEADER_DOT,
    )
    d.line((right_start, cy, right_end, cy), fill=COLOR_HEADER_LINE, width=2)


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
    """v4: premium yorqin web style + 3D emoji."""
    settings = get_settings()
    W, H = size

    home = _normalize_times(region_times)
    mosq = _normalize_times(masjid_times)

    has_mosq = any(mosq.get(p) for p in ALL_PRAYERS)
    if has_mosq:
        _apply_fallback(home, mosq)

    # ============== Fon ==============
    img = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    bg = _make_3stop_gradient(
        W, H, COLOR_BG_TOP, COLOR_BG_MID, COLOR_BG_BOTTOM
    ).convert("RGBA")
    img.paste(bg, (0, 0))
    d = ImageDraw.Draw(img)

    # ============== Fontlar ==============
    f_title = _load_font(FONT_FILES["title"], int(0.062 * H))
    _try_variant(f_title, "Bold")
    f_sub = _load_font(FONT_FILES["subtitle"], int(0.028 * H))
    f_card_name = _load_font(FONT_FILES["name"], int(0.026 * H))
    _try_variant(f_card_name, "SemiBold")
    f_card_time = _load_font(FONT_FILES["time"], int(0.090 * H))
    _try_variant(f_card_time, "Bold")
    f_card_sub = _load_font(FONT_FILES["subtitle"], int(0.022 * H))
    _try_variant(f_card_sub, "SemiBold")
    f_badge = _load_font(FONT_FILES["subtitle"], int(0.018 * H))
    _try_variant(f_badge, "Bold")
    f_footer = _load_font(FONT_FILES["subtitle"], int(0.018 * H))

    # ============== Header (Ka'ba + city + ornament) ==============
    kaaba_size = int(0.075 * H)
    kaaba = _load_emoji("kaaba.png", kaaba_size)

    title_text = region_name.upper()
    title_bbox = d.textbbox((0, 0), title_text, font=f_title)
    title_w = title_bbox[2] - title_bbox[0]

    header_y = int(0.080 * H)
    if kaaba:
        kw = kaaba.size[0]
        gap = 16
        total_w = kw + gap + title_w
        sx = (W - total_w) // 2
        img.alpha_composite(kaaba, (sx, header_y - kaaba.size[1] // 2))
        d.text(
            (sx + kw + gap, header_y),
            title_text,
            font=f_title, fill=COLOR_HEADER_TEXT, anchor="lm",
        )
    else:
        total_w = title_w
        d.text((W // 2, header_y), title_text,
               font=f_title, fill=COLOR_HEADER_TEXT, anchor="mm")

    # Ornament chiziqlari (shahar nomi atrofida)
    _draw_header_ornament(
        d, cx=W // 2, cy=header_y, total_w=total_w + (kaaba.size[0] + 16 if kaaba else 0),
    )

    # Sanalar
    d.text(
        (W // 2, int(0.142 * H)),
        milodiy,
        font=f_sub, fill=COLOR_HEADER_TEXT, anchor="mm",
    )
    d.text(
        (W // 2, int(0.178 * H)),
        hijriy,
        font=f_sub, fill=COLOR_HEADER_DIM, anchor="mm",
    )

    # ============== Cards 3x2 grid ==============
    card_margin_x = int(0.05 * W)
    card_gap_x = int(0.025 * W)
    card_gap_y = int(0.022 * H)
    grid_top = int(0.225 * H)
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

        # 1) Multi-layer drop shadow
        _draw_multi_shadow(img, x, y, card_w, card_h, radius)

        # 2) Card body (subtle gradient)
        if is_highlighted:
            card = _make_card(
                card_w, card_h, radius,
                COLOR_CARD_HIGHLIGHT_TOP, COLOR_CARD_HIGHLIGHT_BOTTOM,
            )
        else:
            card = _make_card(
                card_w, card_h, radius,
                COLOR_CARD_TOP, COLOR_CARD_BOTTOM,
            )
        img.alpha_composite(card, (x, y))

        # 3) Top accent stripe
        accent = COLOR_ACCENT.get(prayer, (200, 200, 200))
        _draw_top_accent(img, x, y, card_w, card_h, radius, accent)

        # 4) Gold glow (highlighted)
        if is_highlighted:
            _draw_gold_glow_double(img, x, y, x2, y2, radius)

        # 5) Card content — SIDE-BY-SIDE: emoji chap, matn o'ng
        prayer_mosq = mosq.get(prayer)
        show_jamoat = has_mosq and bool(prayer_mosq)

        # Emoji (chap tomon, vertikal markaz)
        emoji_size = int(card_h * 0.62)
        emoji_img = _load_emoji(EMOJI_FILES.get(prayer, ""), emoji_size)
        if emoji_img:
            ex = x + int(card_w * 0.06)
            ey = y + (card_h - emoji_img.size[1]) // 2
            img.alpha_composite(emoji_img, (ex, ey))

        # Matn maydoni o'ng tomonda (left-aligned)
        tx = x + int(card_w * 0.44)

        # Prayer name (yuqori)
        name_y = y + int(card_h * (0.30 if show_jamoat else 0.35))
        d.text(
            (tx, name_y),
            prayer.upper(),
            font=f_card_name, fill=COLOR_TEXT_NAME, anchor="lm",
        )

        # Time (markaz — eng katta)
        time_y = y + int(card_h * (0.58 if show_jamoat else 0.62))
        d.text(
            (tx, time_y),
            home.get(prayer) or EMPTY_MARK,
            font=f_card_time, fill=COLOR_TEXT_TIME, anchor="lm",
        )

        # Jamoat (pastki)
        if show_jamoat:
            d.text(
                (tx, y + int(card_h * 0.86)),
                f"Jamoat  {prayer_mosq}",
                font=f_card_sub, fill=COLOR_TEXT_JAMOAT, anchor="lm",
            )

        # KEYINGI badge
        if is_highlighted:
            badge_text = "KEYINGI"
            bbox = d.textbbox((0, 0), badge_text, font=f_badge)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            pad_x, pad_y = 12, 7
            bx = x2 - tw - pad_x * 2 - 12
            by = y + 14
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

    # ============== Footer ornament + attribution ==============
    foot_y = int(0.972 * H)
    # Oltin chiziqcha
    line_w = int(0.20 * W)
    d.line(
        ((W - line_w) // 2, foot_y - 18, (W + line_w) // 2, foot_y - 18),
        fill=COLOR_HEADER_DOT, width=2,
    )
    attribution = (
        "islomapi.uz · O'zbekiston musulmonlari idorasi"
        if has_mosq
        else "Aladhan API · ISNA · Hanafi"
    )
    d.text(
        (W // 2, foot_y),
        attribution,
        font=f_footer, fill=COLOR_HEADER_DIM, anchor="mm",
    )

    # ============== Saqlash ==============
    if out_filename:
        out_path = settings.images_dir / out_filename
    else:
        out_path = settings.images_dir / f"{_safe_filename(region_name)}.png"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out_path, optimize=True)
    logger.debug("Rasm saqlandi: {}", out_path)
    return out_path


__all__ = ["make_prayer_image"]
