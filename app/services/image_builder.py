"""Namoz vaqtlari rasmini yasaydi (Pillow) — v3: yorqin web style + 3D emoji.

Yangi dizayn:
- Yorqin (light) gradient fon — peach → rose
- Sof oq kartlar yumshoq soya bilan (modern web aesthetic)
- Har namoz uchun maxsus 3D emoji (Microsoft Fluent UI Emoji)
- Header'da Ka'ba emoji + shahar nomi
- Keyingi farz oltin halqa + KEYINGI badge bilan ajratiladi
- Per-prayer accent rang (vaqt ranglar bilan eslatish)
"""
from __future__ import annotations

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

#: Namoz uchun 3D emoji fayllari (static/emojis/)
EMOJI_FILES: dict[str, str] = {
    "Bomdod":   "sunrise.png",
    "Quyosh":   "sunrise_mt.png",
    "Peshin":   "sun_face.png",
    "Asr":      "sun_cloud.png",
    "Shom":     "sunset.png",
    "Xufton":   "moon.png",
}

EMPTY_MARK = "—"

# ============== Yorqin web ranglar ==============
# Background gradient (warm peach → rose)
COLOR_BG_TOP = (255, 226, 184)           # peach
COLOR_BG_BOTTOM = (255, 218, 224)        # rose pastel

# Cards
COLOR_CARD = (255, 255, 255)             # toza oq
COLOR_CARD_HIGHLIGHT = (255, 251, 240)   # bir oz issiqroq oq (highlighted)

# Per-prayer accent colors — vaqt ranglar bilan eslatish
COLOR_ACCENT: dict[str, tuple[int, int, int]] = {
    "Bomdod":  (255, 107, 53),    # vivid orange — sahar
    "Quyosh":  (255, 159, 28),    # bright orange-yellow
    "Peshin":  (78, 205, 196),    # turquoise — kunduz
    "Asr":     (255, 165, 0),     # amber
    "Shom":    (255, 107, 107),   # coral — kun botishi
    "Xufton":  (108, 92, 231),    # purple — tun
}

# Text
COLOR_TEXT_NAME = (75, 85, 99)           # kulrang prayer name
COLOR_TEXT_TIME = (17, 24, 39)           # to'q grafit time
COLOR_TEXT_JAMOAT = (75, 99, 75)         # to'q yashil jamoat
COLOR_DIVIDER = (229, 231, 235)          # och kulrang chiziqcha

# Header
COLOR_HEADER_TEXT = (45, 55, 72)         # to'q grafit
COLOR_HEADER_DIM = (107, 114, 128)       # och kulrang
COLOR_HEADER_LINE = (203, 213, 225)      # ajratuvchi chiziq

# Highlighted card (KEYINGI)
COLOR_GOLD = (218, 165, 32)              # oltin
COLOR_GOLD_GLOW = (255, 215, 100)        # yorqinroq oltin


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


def _make_vertical_gradient(
    w: int, h: int, top: tuple[int, int, int], bottom: tuple[int, int, int]
) -> Image.Image:
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        ratio = y / max(h - 1, 1)
        r = int(top[0] + (bottom[0] - top[0]) * ratio)
        g = int(top[1] + (bottom[1] - top[1]) * ratio)
        b = int(top[2] + (bottom[2] - top[2]) * ratio)
        grad.putpixel((0, y), (r, g, b))
    return grad.resize((w, h))


def _make_card(
    w: int, h: int, radius: int, fill: tuple[int, int, int]
) -> Image.Image:
    """Sof oq (yoki ozgina shartli) rounded rect card (RGBA)."""
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, w, h), radius=radius, fill=255,
    )
    body = Image.new("RGB", (w, h), fill)
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    card.paste(body, (0, 0), mask)
    return card


def _make_shadow(
    w: int, h: int, radius: int, *, blur: int = 22, opacity: int = 60
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
    """Highlighted card uchun oltin glow + halqa."""
    pad = 14
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle(
        (x - pad, y - pad, x2 + pad, y2 + pad),
        radius=radius + pad,
        outline=COLOR_GOLD_GLOW + (170,),
        width=10,
    )
    glow = glow.filter(ImageFilter.GaussianBlur(10))
    img.alpha_composite(glow)

    ring = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ring).rounded_rectangle(
        (x - 3, y - 3, x2 + 3, y2 + 3),
        radius=radius + 3,
        outline=COLOR_GOLD + (255,),
        width=4,
    )
    img.alpha_composite(ring)


def _load_emoji(filename: str, target_size: int) -> Image.Image | None:
    """3D emoji PNG ni yuklab, kerakli o'lchamga keltiradi."""
    settings = get_settings()
    path = settings.static_dir / "emojis" / filename
    if not path.exists():
        logger.debug("Emoji topilmadi: {}", path)
        return None
    try:
        em = Image.open(path).convert("RGBA")
        em.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)
        return em
    except (OSError, ValueError) as e:
        logger.debug("Emoji yuklanmadi {}: {}", path, e)
        return None


def _draw_top_accent(
    img: Image.Image, x: int, y: int, w: int, h: int, radius: int,
    color: tuple[int, int, int],
) -> None:
    """Card yuqori qismida ingichka rangli aksent (faqat top-radius bo'yicha)."""
    stripe_h = 6
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, w, h), radius=radius, fill=255,
    )
    body = Image.new("RGB", (w, stripe_h), color)
    layer.paste(body, (0, 0))
    # Mask'ning faqat yuqori qatlamini olamiz
    top_mask = Image.new("L", (w, h), 0)
    top_mask.paste(mask.crop((0, 0, w, stripe_h)), (0, 0))
    layer.putalpha(top_mask)
    img.alpha_composite(layer, (x, y))


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
    v3: yorqin web style + 3D emoji card grid.
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
    img = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    bg = _make_vertical_gradient(W, H, COLOR_BG_TOP, COLOR_BG_BOTTOM).convert("RGBA")
    img.paste(bg, (0, 0))
    d = ImageDraw.Draw(img)

    # ============== Fontlar ==============
    f_title = _load_font(FONT_FILES["title"], int(0.060 * H))
    _try_variant(f_title, "Bold")
    f_sub = _load_font(FONT_FILES["subtitle"], int(0.028 * H))
    f_card_name = _load_font(FONT_FILES["name"], int(0.028 * H))
    _try_variant(f_card_name, "SemiBold")
    f_card_time = _load_font(FONT_FILES["time"], int(0.080 * H))
    _try_variant(f_card_time, "Bold")
    f_card_sub = _load_font(FONT_FILES["subtitle"], int(0.024 * H))
    _try_variant(f_card_sub, "SemiBold")
    f_badge = _load_font(FONT_FILES["subtitle"], int(0.020 * H))
    _try_variant(f_badge, "Bold")
    f_footer = _load_font(FONT_FILES["subtitle"], int(0.020 * H))

    # ============== Header ==============
    # Ka'ba emoji + shahar nomi
    kaaba = _load_emoji("kaaba.png", int(0.075 * H))
    header_y_center = int(0.080 * H)
    if kaaba:
        kaaba_w = kaaba.size[0]
        # Ka'ba va matn birgalikda markazga
        title_bbox = d.textbbox((0, 0), region_name.upper(), font=f_title)
        title_w = title_bbox[2] - title_bbox[0]
        gap = 18
        total_w = kaaba_w + gap + title_w
        start_x = (W - total_w) // 2
        img.alpha_composite(
            kaaba, (start_x, header_y_center - kaaba.size[1] // 2),
        )
        d.text(
            (start_x + kaaba_w + gap, header_y_center),
            region_name.upper(),
            font=f_title, fill=COLOR_HEADER_TEXT, anchor="lm",
        )
    else:
        d.text(
            (W // 2, header_y_center),
            region_name.upper(),
            font=f_title, fill=COLOR_HEADER_TEXT, anchor="mm",
        )

    d.text(
        (W // 2, int(0.140 * H)),
        milodiy,
        font=f_sub, fill=COLOR_HEADER_TEXT, anchor="mm",
    )
    d.text(
        (W // 2, int(0.175 * H)),
        hijriy,
        font=f_sub, fill=COLOR_HEADER_DIM, anchor="mm",
    )
    d.line(
        (int(0.32 * W), int(0.205 * H), W - int(0.32 * W), int(0.205 * H)),
        fill=COLOR_HEADER_LINE, width=2,
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

        # 1) Drop shadow (yumshoq, light theme uchun nozik)
        shadow = _make_shadow(card_w, card_h, radius, blur=22, opacity=55)
        img.alpha_composite(shadow, (x - 44, y - 38))

        # 2) Card body
        fill = COLOR_CARD_HIGHLIGHT if is_highlighted else COLOR_CARD
        card = _make_card(card_w, card_h, radius, fill)
        img.alpha_composite(card, (x, y))

        # 3) Top accent stripe (har namoz uchun rang)
        accent = COLOR_ACCENT.get(prayer, (200, 200, 200))
        _draw_top_accent(img, x, y, card_w, card_h, radius, accent)

        # 4) Oltin halqa (highlighted)
        if is_highlighted:
            _draw_gold_ring(img, x, y, x2, y2, radius)

        # 5) Card kontenti
        cx = (x + x2) // 2

        # Emoji (chap yoki markazda yuqori)
        emoji_size = int(card_h * 0.36)
        emoji_img = _load_emoji(EMOJI_FILES.get(prayer, ""), emoji_size)
        if emoji_img:
            img.alpha_composite(
                emoji_img,
                (cx - emoji_img.size[0] // 2, y + int(card_h * 0.10)),
            )

        prayer_mosq = mosq.get(prayer)
        show_jamoat = has_mosq and bool(prayer_mosq)

        # Prayer name (emoji ostida)
        name_y = y + int(card_h * 0.55)
        d.text(
            (cx, name_y),
            prayer.upper(),
            font=f_card_name, fill=COLOR_TEXT_NAME, anchor="mm",
        )

        # Time (katta)
        time_y = y + int(card_h * 0.74) if show_jamoat else y + int(card_h * 0.78)
        d.text(
            (cx, time_y),
            home.get(prayer) or EMPTY_MARK,
            font=f_card_time, fill=COLOR_TEXT_TIME, anchor="mm",
        )

        if show_jamoat:
            div_y = y + int(card_h * 0.90)
            div_pad = int(card_w * 0.28)
            d.line(
                (x + div_pad, div_y, x2 - div_pad, div_y),
                fill=COLOR_DIVIDER, width=1,
            )
            d.text(
                (cx, y + int(card_h * 0.96)),
                f"Jamoat  {prayer_mosq}",
                font=f_card_sub, fill=COLOR_TEXT_JAMOAT, anchor="mm",
            )

        # 6) "KEYINGI" badge highlighted card uchun
        if is_highlighted:
            badge_text = "KEYINGI"
            bbox = d.textbbox((0, 0), badge_text, font=f_badge)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            pad_x, pad_y = 14, 8
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

    # ============== Footer ==============
    attribution = (
        "islomapi.uz · O'zbekiston musulmonlari idorasi"
        if has_mosq
        else "Aladhan API · ISNA · Hanafi"
    )
    d.text(
        (W // 2, int(0.978 * H)),
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
