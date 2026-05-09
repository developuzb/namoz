"""Namoz vaqtlari rasmini yasaydi (Pillow) — v5: Islamic premium.

Yangi konsepsiya:
- Real fotograf hissi: sunset osmon gradient + yulduzlar + yarim oy + masjid silueti
- Hero card (KEYINGI namoz uchun katta) + 5 kichik kart pastda
- Glass-morphism cardlar (semi-transparent + blur)
- Klassik Islamic ornamentlar (oltin chiziqcha, yulduzli pattern)
- 3D emoji'lar saqlanadi (Microsoft Fluent UI)
"""
from __future__ import annotations

import math
import random
import re
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from app.core.config import get_settings
from app.core.constants import ALL_PRAYERS, FARZ_PRAYERS
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

# ============== Sunset osmon palette (4-stop) ==============
COLOR_SKY_TOP = (38, 48, 95)         # navy yuqori
COLOR_SKY_HIGH = (78, 56, 122)       # binafsha
COLOR_SKY_MID = (210, 95, 110)       # qizg'ish-pushti
COLOR_SKY_LOW = (244, 156, 102)      # to'q sariq
COLOR_SKY_BOTTOM = (15, 25, 60)      # to'q ko'k (silhouette ostida)

COLOR_SILHOUETTE = (5, 8, 25)        # qora-ko'k masjid silueti
COLOR_STAR = (255, 250, 230)
COLOR_MOON = (255, 240, 200)

# Glass card
COLOR_GLASS_OVERLAY = (255, 255, 255, 165)  # oq, yarim shaffof
COLOR_GLASS_HIGHLIGHT = (255, 252, 240, 215)  # KEYINGI uchun ozroq qoyuq

# Per-prayer accent
COLOR_ACCENT: dict[str, tuple[int, int, int]] = {
    "Bomdod":  (255, 121, 84),
    "Quyosh":  (255, 167, 38),
    "Peshin":  (38, 198, 218),
    "Asr":     (255, 152, 0),
    "Shom":    (244, 81, 108),
    "Xufton":  (126, 87, 194),
}

# Text on glass (light bg) — to'q
COLOR_TEXT_NAME = (60, 50, 80)
COLOR_TEXT_TIME = (20, 20, 40)
COLOR_TEXT_JAMOAT = (70, 90, 70)
COLOR_DIVIDER = (200, 200, 200)

# Header / footer (oq matn osmonda)
COLOR_HEADER_TEXT = (255, 250, 240)
COLOR_HEADER_DIM = (220, 215, 230)
COLOR_HEADER_LINE = (255, 220, 180, 180)
COLOR_HEADER_DOT = (255, 200, 130)

# Highlighted gold
COLOR_GOLD = (218, 165, 32)
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


# ============== BG: sunset gradient + stars + moon + silhouette ==============

def _make_sky_gradient(W: int, H: int) -> Image.Image:
    """4-stop sunset gradient — yulduzlar va silhouette uchun fon."""
    stops = [
        (0.00, COLOR_SKY_TOP),
        (0.30, COLOR_SKY_HIGH),
        (0.55, COLOR_SKY_MID),
        (0.78, COLOR_SKY_LOW),
        (1.00, COLOR_SKY_BOTTOM),
    ]
    grad = Image.new("RGB", (1, H))
    for y in range(H):
        ratio = y / max(H - 1, 1)
        # Topdan past-pastiga yaqin stop'larni topib interpolate
        for i in range(len(stops) - 1):
            r1, c1 = stops[i]
            r2, c2 = stops[i + 1]
            if r1 <= ratio <= r2:
                t = (ratio - r1) / max(r2 - r1, 0.0001)
                r = int(c1[0] + (c2[0] - c1[0]) * t)
                g = int(c1[1] + (c2[1] - c1[1]) * t)
                b = int(c1[2] + (c2[2] - c1[2]) * t)
                grad.putpixel((0, y), (r, g, b))
                break
    return grad.resize((W, H))


def _draw_stars(img: Image.Image, count: int = 90) -> None:
    """Twinkling yulduzlar — yuqori 50% da."""
    rng = random.Random(2026)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    W, H = img.size
    for _ in range(count):
        x = rng.randint(0, W)
        y = rng.randint(0, int(H * 0.50))
        size = rng.choice([1, 1, 2, 2, 2, 3])
        opacity = rng.randint(120, 240)
        d.ellipse(
            (x - size, y - size, x + size, y + size),
            fill=COLOR_STAR + (opacity,),
        )
    img.alpha_composite(layer)


def _draw_crescent(img: Image.Image, cx: int, cy: int, r: int) -> None:
    """Yarim oy (crescent moon) — top-right area."""
    size = r * 2 + 20
    full_mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(full_mask).ellipse((10, 10, size - 10, size - 10), fill=255)

    cut_mask = Image.new("L", (size, size), 0)
    shift = int(r * 0.42)
    ImageDraw.Draw(cut_mask).ellipse(
        (10 + shift, 10, size - 10 + shift, size - 10), fill=255,
    )
    crescent_mask = ImageChops.subtract(full_mask, cut_mask)

    # Glow (ortda blur)
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    color_img = Image.new("RGBA", (size, size), COLOR_MOON + (255,))
    glow.paste(color_img, (0, 0), crescent_mask)
    glow_blur = glow.filter(ImageFilter.GaussianBlur(8))

    img.alpha_composite(glow_blur, (cx - size // 2, cy - size // 2))
    img.alpha_composite(glow, (cx - size // 2, cy - size // 2))


def _draw_mosque_silhouette(img: Image.Image) -> None:
    """Pastida masjid silueti — minimalist, simvolik."""
    W, H = img.size
    base_y = int(H * 0.93)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    color = COLOR_SILHOUETTE + (255,)

    cx = W // 2

    # Pastki yer chizig'i
    d.rectangle((0, base_y + 30, W, H), fill=color)

    # Markaziy gumbaz
    dome_r = int(W * 0.085)
    d.pieslice(
        (cx - dome_r, base_y - dome_r * 2, cx + dome_r, base_y),
        180, 360, fill=color,
    )
    # Markaziy bino
    body_w = int(W * 0.22)
    body_h = int(W * 0.06)
    d.rectangle(
        (cx - body_w // 2, base_y, cx + body_w // 2, base_y + 30),
        fill=color,
    )

    # Yon kichik gumbazlar
    side_dome_r = int(W * 0.045)
    side_offset = int(W * 0.14)
    for sign in (-1, 1):
        x = cx + sign * side_offset
        d.pieslice(
            (x - side_dome_r, base_y - side_dome_r * 2, x + side_dome_r, base_y),
            180, 360, fill=color,
        )

    # Minoralar (left + right)
    minaret_w = int(W * 0.018)
    minaret_h = int(W * 0.16)
    minaret_top_r = int(W * 0.014)
    for sign in (-1, 1):
        mx = cx + sign * int(W * 0.27)
        # Tana
        d.rectangle(
            (mx - minaret_w // 2, base_y - minaret_h,
             mx + minaret_w // 2, base_y + 30),
            fill=color,
        )
        # Tepa gumbaz
        d.pieslice(
            (mx - minaret_top_r, base_y - minaret_h - minaret_top_r * 2,
             mx + minaret_top_r, base_y - minaret_h),
            180, 360, fill=color,
        )
        # Spire
        spire_top = base_y - minaret_h - minaret_top_r * 2 - 22
        d.line(
            (mx, base_y - minaret_h - minaret_top_r * 2, mx, spire_top),
            fill=color, width=2,
        )

    img.alpha_composite(layer)


# ============== Glass cards ==============

def _make_glass_card(
    bg: Image.Image, x: int, y: int, w: int, h: int, radius: int,
    *, overlay_color: tuple[int, int, int, int] = COLOR_GLASS_OVERLAY,
    blur: int = 22,
) -> Image.Image:
    """Glassmorphism card — bg ning shu joyini blur qilib + oqartirib qaytaradi."""
    region = bg.crop((x, y, x + w, y + h)).convert("RGBA")
    region = region.filter(ImageFilter.GaussianBlur(blur))
    overlay = Image.new("RGBA", (w, h), overlay_color)
    region = Image.alpha_composite(region, overlay)

    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, w, h), radius=radius, fill=255,
    )
    glass = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glass.paste(region, (0, 0), mask)
    return glass


def _make_shadow(
    w: int, h: int, radius: int, *, blur: int = 22, opacity: int = 90
) -> Image.Image:
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
    pad = 18
    glow_outer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow_outer).rounded_rectangle(
        (x - pad, y - pad, x2 + pad, y2 + pad),
        radius=radius + pad,
        outline=COLOR_GOLD_GLOW_OUT + (140,),
        width=12,
    )
    glow_outer = glow_outer.filter(ImageFilter.GaussianBlur(12))
    img.alpha_composite(glow_outer)

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


def _draw_text_shadow(
    d: ImageDraw.ImageDraw, xy: tuple[int, int], text: str,
    font: ImageFont.FreeTypeFont, fill,
    *, anchor: str = "mm",
    shadow_color: tuple[int, int, int, int] = (0, 0, 0, 130),
    shadow_offset: int = 2,
) -> None:
    """Header matni uchun nozik soya (chiroyli o'qilishi uchun)."""
    d.text(
        (xy[0] + shadow_offset, xy[1] + shadow_offset),
        text, font=font, fill=shadow_color, anchor=anchor,
    )
    d.text(xy, text, font=font, fill=fill, anchor=anchor)


def _next_prayer(home: dict[str, str], highlight: str | None) -> str:
    """Hero card uchun ko'rsatiladigan namozni aniqlaydi.

    Birinchi navbatda — caller bergan `highlight` (PostService keyingi farzni topadi).
    Agar yo'q bo'lsa — birinchi farz (Bomdod). Hero har doim ko'rsatiladi.
    """
    if highlight and highlight in home:
        return highlight
    for p in FARZ_PRAYERS:
        if home.get(p):
            return p
    return "Bomdod"


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
    """v5: Sunset osmon + masjid silueti + Hero glass card + 5 kichik glass."""
    settings = get_settings()
    W, H = size

    home = _normalize_times(region_times)
    mosq = _normalize_times(masjid_times)

    has_mosq = any(mosq.get(p) for p in ALL_PRAYERS)
    if has_mosq:
        _apply_fallback(home, mosq)

    # ============== Sunset BG ==============
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sky = _make_sky_gradient(W, H).convert("RGBA")
    img.paste(sky, (0, 0))
    _draw_stars(img, count=85)
    # Yarim oy yuqori-o'ng
    _draw_crescent(img, cx=int(W * 0.85), cy=int(H * 0.10), r=42)
    # Masjid silueti pastda
    _draw_mosque_silhouette(img)

    # `bg` keyinchalik glass cardlar uchun ishlatamiz
    bg_for_glass = img.copy()

    d = ImageDraw.Draw(img)

    # ============== Fontlar ==============
    f_title = _load_font(FONT_FILES["title"], int(0.058 * H))
    _try_variant(f_title, "Bold")
    f_sub = _load_font(FONT_FILES["subtitle"], int(0.026 * H))
    _try_variant(f_sub, "SemiBold")

    f_hero_label = _load_font(FONT_FILES["subtitle"], int(0.024 * H))
    _try_variant(f_hero_label, "Bold")
    f_hero_name = _load_font(FONT_FILES["name"], int(0.038 * H))
    _try_variant(f_hero_name, "SemiBold")
    f_hero_time = _load_font(FONT_FILES["time"], int(0.130 * H))
    _try_variant(f_hero_time, "Bold")
    f_hero_sub = _load_font(FONT_FILES["subtitle"], int(0.024 * H))
    _try_variant(f_hero_sub, "SemiBold")

    f_card_name = _load_font(FONT_FILES["name"], int(0.022 * H))
    _try_variant(f_card_name, "SemiBold")
    f_card_time = _load_font(FONT_FILES["time"], int(0.044 * H))
    _try_variant(f_card_time, "Bold")
    f_card_jamoat = _load_font(FONT_FILES["subtitle"], int(0.018 * H))

    f_footer = _load_font(FONT_FILES["subtitle"], int(0.018 * H))

    # ============== Header (Ka'ba + city + dates) ==============
    kaaba_size = int(0.070 * H)
    kaaba = _load_emoji("kaaba.png", kaaba_size)

    title_text = region_name.upper()
    title_bbox = d.textbbox((0, 0), title_text, font=f_title)
    title_w = title_bbox[2] - title_bbox[0]

    header_y = int(0.075 * H)
    if kaaba:
        kw = kaaba.size[0]
        gap = 16
        total_w = kw + gap + title_w
        sx = (W - total_w) // 2
        img.alpha_composite(kaaba, (sx, header_y - kaaba.size[1] // 2))
        _draw_text_shadow(
            d, (sx + kw + gap, header_y), title_text,
            f_title, fill=COLOR_HEADER_TEXT, anchor="lm",
        )
    else:
        _draw_text_shadow(
            d, (W // 2, header_y), title_text,
            f_title, fill=COLOR_HEADER_TEXT, anchor="mm",
        )

    # Sanalar
    _draw_text_shadow(
        d, (W // 2, int(0.130 * H)), milodiy,
        f_sub, fill=COLOR_HEADER_TEXT, anchor="mm",
    )
    _draw_text_shadow(
        d, (W // 2, int(0.165 * H)), hijriy,
        f_sub, fill=COLOR_HEADER_DIM, anchor="mm",
    )

    # Oltin nuqtali ajratuvchi chiziq
    line_y = int(0.195 * H)
    line_pad = int(0.30 * W)
    d.line((line_pad, line_y, W - line_pad - 12, line_y), fill=(255, 220, 180, 200), width=2)
    d.ellipse((W // 2 - 4, line_y - 4, W // 2 + 4, line_y + 4), fill=COLOR_HEADER_DOT)
    d.line((line_pad + 12, line_y, W // 2 - 8, line_y), fill=(255, 220, 180, 200), width=2)
    d.line((W // 2 + 8, line_y, W - line_pad, line_y), fill=(255, 220, 180, 200), width=2)

    # ============== HERO card (next prayer) ==============
    hero_top = int(0.225 * H)
    hero_bottom = int(0.58 * H)
    hero_x = int(0.055 * W)
    hero_x2 = W - hero_x
    hero_w = hero_x2 - hero_x
    hero_h = hero_bottom - hero_top
    hero_radius = int(0.030 * W)

    hero_prayer = _next_prayer(home, highlight_prayer)

    # Soya
    hero_shadow = _make_shadow(hero_w, hero_h, hero_radius, blur=24, opacity=110)
    img.alpha_composite(hero_shadow, (hero_x - 48, hero_top - 38))

    # Glass card
    overlay = (
        COLOR_GLASS_HIGHLIGHT
        if hero_prayer == highlight_prayer
        else COLOR_GLASS_OVERLAY
    )
    hero_glass = _make_glass_card(
        bg_for_glass, hero_x, hero_top, hero_w, hero_h, hero_radius,
        overlay_color=overlay,
    )
    img.alpha_composite(hero_glass, (hero_x, hero_top))
    _draw_top_accent(
        img, hero_x, hero_top, hero_w, hero_h, hero_radius,
        COLOR_ACCENT.get(hero_prayer, (200, 200, 200)),
    )

    if hero_prayer == highlight_prayer:
        _draw_gold_ring(img, hero_x, hero_top, hero_x2, hero_top + hero_h, hero_radius)

    # Hero kontenti — emoji chap, matn o'ng
    hero_emoji_size = int(hero_h * 0.75)
    hero_emoji = _load_emoji(EMOJI_FILES.get(hero_prayer, ""), hero_emoji_size)
    if hero_emoji:
        ex = hero_x + int(hero_w * 0.05)
        ey = hero_top + (hero_h - hero_emoji.size[1]) // 2
        img.alpha_composite(hero_emoji, (ex, ey))

    tx = hero_x + int(hero_w * 0.45)
    label_text = "KEYINGI NAMOZ" if hero_prayer == highlight_prayer else "BUGUNGI NAMOZLAR"
    d.text(
        (tx, hero_top + int(hero_h * 0.18)),
        label_text,
        font=f_hero_label, fill=COLOR_GOLD, anchor="lm",
    )
    d.text(
        (tx, hero_top + int(hero_h * 0.32)),
        hero_prayer.upper(),
        font=f_hero_name, fill=COLOR_TEXT_NAME, anchor="lm",
    )
    d.text(
        (tx, hero_top + int(hero_h * 0.58)),
        home.get(hero_prayer) or EMPTY_MARK,
        font=f_hero_time, fill=COLOR_TEXT_TIME, anchor="lm",
    )
    if has_mosq and mosq.get(hero_prayer):
        d.text(
            (tx, hero_top + int(hero_h * 0.84)),
            f"Jamoat  {mosq.get(hero_prayer)}",
            font=f_hero_sub, fill=COLOR_TEXT_JAMOAT, anchor="lm",
        )

    # ============== 5 kichik kartlar pastda ==============
    other_prayers = [p for p in ALL_PRAYERS if p != hero_prayer]
    n_small = len(other_prayers)

    small_top = int(0.605 * H)
    small_bottom = int(0.86 * H)
    small_h = small_bottom - small_top
    small_margin = int(0.045 * W)
    small_gap = int(0.014 * W)
    available_w = W - 2 * small_margin - small_gap * (n_small - 1)
    small_w = available_w // n_small
    small_radius = int(0.022 * W)

    for i, prayer in enumerate(other_prayers):
        sx = small_margin + i * (small_w + small_gap)
        sy = small_top
        sx2 = sx + small_w
        sy2 = sy + small_h

        is_highlighted = (prayer == highlight_prayer)

        # Soya
        sm_shadow = _make_shadow(small_w, small_h, small_radius, blur=18, opacity=90)
        img.alpha_composite(sm_shadow, (sx - 36, sy - 28))

        # Glass card
        ov = COLOR_GLASS_HIGHLIGHT if is_highlighted else COLOR_GLASS_OVERLAY
        sm_glass = _make_glass_card(
            bg_for_glass, sx, sy, small_w, small_h, small_radius,
            overlay_color=ov, blur=18,
        )
        img.alpha_composite(sm_glass, (sx, sy))
        _draw_top_accent(
            img, sx, sy, small_w, small_h, small_radius,
            COLOR_ACCENT.get(prayer, (200, 200, 200)),
        )
        if is_highlighted:
            _draw_gold_ring(img, sx, sy, sx2, sy2, small_radius)

        # Vertical layout: emoji top, name middle, time bottom
        cx = (sx + sx2) // 2
        em_size = int(small_h * 0.42)
        em = _load_emoji(EMOJI_FILES.get(prayer, ""), em_size)
        if em:
            img.alpha_composite(
                em, (cx - em.size[0] // 2, sy + int(small_h * 0.08)),
            )

        d.text(
            (cx, sy + int(small_h * 0.62)),
            prayer.upper(),
            font=f_card_name, fill=COLOR_TEXT_NAME, anchor="mm",
        )
        d.text(
            (cx, sy + int(small_h * 0.85)),
            home.get(prayer) or EMPTY_MARK,
            font=f_card_time, fill=COLOR_TEXT_TIME, anchor="mm",
        )

    # ============== Footer ==============
    foot_y = int(0.965 * H)
    attribution = (
        "islomapi.uz · O'zbekiston musulmonlari idorasi"
        if has_mosq
        else "Aladhan API · ISNA · Hanafi"
    )
    _draw_text_shadow(
        d, (W // 2, foot_y), attribution,
        f_footer, fill=COLOR_HEADER_DIM, anchor="mm",
    )

    # ============== Saqlash ==============
    if out_filename:
        out_path = settings.images_dir / out_filename
    else:
        out_path = settings.images_dir / f"{_safe_filename(region_name)}.png"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out_path, optimize=True, quality=92)
    logger.debug("Rasm saqlandi: {}", out_path)
    return out_path


__all__ = ["make_prayer_image"]
