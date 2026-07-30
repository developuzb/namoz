"""Namoz vaqtlari rasmini yasaydi (Pillow) — v7: To'q iOS islomiy.

Qashqadaryo plakati bilan bir xil palitra (uyg'un brending):
- Chuqur yashil-charcoal gradient fon + yumshoq nur (glow)
- Hero card (KEYINGI namoz) — vibrant aksent gradient, katta oq raqam
- 2x3 grid: 6 namoz to'q surface kartlarda, oltin/aksent matn
- Oltin sarlavha, kaaba/pin ikon, iOS pill ko'rinishidagi sana
- Microsoft Fluent 3D emoji'lar
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from app.core.config import get_settings
from app.core.constants import ALL_PRAYERS, FARZ_PRAYERS
from app.core.logger import logger
from app.services.backdrop import aqsa_backdrop
from app.utils.time_utils import clean_hhmm

#: Chiqish o'lchami (yakuniy PNG). Sifat uchun ichkarida SS barobar
#: kattaroq render qilinib, LANCZOS bilan kichraytiriladi (supersampling).
DEFAULT_SIZE: tuple[int, int] = (1350, 1350)
SS: int = 2  # supersample koeffitsienti (2 = 2x aniqlik)

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

# ============== Kunduzgi (light) islomiy palette ==============
COLOR_BG_TOP   = (252, 250, 245)      # issiq oq (cream)
COLOR_BG_BOT   = (236, 242, 236)      # och yashil-kul
COLOR_GLOW     = (208, 224, 210)      # header ortida yumshoq salqin nur

COLOR_GOLD     = (176, 138, 58)       # to'q oltin (och fonda kontrast)
COLOR_GOLD_DK  = (140, 106, 42)
COLOR_WHITE    = (255, 255, 255)      # hero (rangli) kart ustidagi matn uchun
COLOR_INK      = (30, 48, 40)         # asosiy to'q matn (och fonda)
COLOR_DIM      = (112, 126, 116)      # ikkilamchi matn

COLOR_SURFACE  = (255, 255, 255)      # oq kart yuzasi
COLOR_BORDER   = (24, 48, 36, 34)     # nozik to'q hairline ramka
COLOR_SHADOW   = (26, 46, 36)         # kart ostidagi yumshoq soya

# Per-prayer accent (iOS, kun davriga mos) — hero kart gradienti uchun
COLOR_ACCENT: dict[str, tuple[int, int, int]] = {
    "Bomdod":  (96, 170, 255),
    "Quyosh":  (255, 190, 78),
    "Peshin":  (255, 128, 99),
    "Asr":     (255, 158, 72),
    "Shom":    (236, 118, 156),
    "Xufton":  (132, 122, 232),
}
# To'qroq variant — hero gradient pastki, va oq kartda matn/halqa uchun
COLOR_ACCENT_DARK: dict[str, tuple[int, int, int]] = {
    "Bomdod":  (44, 104, 182),
    "Quyosh":  (190, 130, 34),
    "Peshin":  (196, 70, 50),
    "Asr":     (190, 104, 30),
    "Shom":    (170, 62, 104),
    "Xufton":  (82, 72, 178),
}


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


def _next_prayer(home: dict[str, str], highlight: str | None) -> str:
    if highlight and highlight in home:
        return highlight
    for p in FARZ_PRAYERS:
        if home.get(p):
            return p
    return "Bomdod"


# ============== Background ==============

def _make_bg(W: int, H: int) -> Image.Image:
    """Issiq oq (cream) vertikal gradient + header ortida yumshoq nur."""
    grad = Image.new("RGB", (1, H))
    for y in range(H):
        t = y / max(H - 1, 1)
        grad.putpixel((0, y), (
            int(COLOR_BG_TOP[0] + (COLOR_BG_BOT[0] - COLOR_BG_TOP[0]) * t),
            int(COLOR_BG_TOP[1] + (COLOR_BG_BOT[1] - COLOR_BG_TOP[1]) * t),
            int(COLOR_BG_TOP[2] + (COLOR_BG_BOT[2] - COLOR_BG_TOP[2]) * t),
        ))
    img = grad.resize((W, H)).convert("RGBA")
    glow = _radial_glow(int(W * 0.95), COLOR_GLOW, 70)
    img.alpha_composite(glow, (W // 2 - glow.size[0] // 2, int(-H * 0.22)))
    return img


def _radial_glow(diam: int, color: tuple[int, int, int], max_alpha: int) -> Image.Image:
    grad = Image.radial_gradient("L").resize((diam, diam))
    alpha = ImageOps.invert(grad).point(lambda v: int((v / 255) * max_alpha))
    layer = Image.new("RGBA", (diam, diam), (*color, 0))
    layer.putalpha(alpha)
    return layer


# ============== Cards ==============

def _make_vgradient(
    w: int, h: int, c_top: tuple[int, int, int], c_bot: tuple[int, int, int]
) -> Image.Image:
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        grad.putpixel((0, y), (
            int(c_top[0] + (c_bot[0] - c_top[0]) * t),
            int(c_top[1] + (c_bot[1] - c_top[1]) * t),
            int(c_top[2] + (c_bot[2] - c_top[2]) * t),
        ))
    return grad.resize((w, h)).convert("RGBA")


def _rounded(src: Image.Image, radius: int) -> Image.Image:
    w, h = src.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(src, (0, 0), mask)
    return out


def _surface(
    img: Image.Image, x: int, y: int, w: int, h: int, radius: int,
    *, fill: Image.Image | tuple[int, int, int] = COLOR_SURFACE,
    border: tuple[int, int, int, int] | None = COLOR_BORDER,
    shadow: bool = True,
) -> None:
    """Oq rounded surface — yumshoq soya + nozik hairline ramka."""
    # Yumshoq soya (kart o'lchamidagi kichik tile — arzon blur)
    if shadow:
        pad = max(radius, h // 8)
        tile = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
        ImageDraw.Draw(tile).rounded_rectangle(
            (pad, pad, pad + w, pad + h), radius=radius, fill=(*COLOR_SHADOW, 55),
        )
        tile = tile.filter(ImageFilter.GaussianBlur(max(4, h // 22)))
        img.alpha_composite(tile, (x - pad, y - pad + max(3, h // 32)))

    if isinstance(fill, Image.Image):
        card = _rounded(fill, radius)
    else:
        solid = Image.new("RGBA", (w, h), (*fill, 255))
        card = _rounded(solid, radius)
    img.alpha_composite(card, (x, y))
    if border is not None:
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).rounded_rectangle(
            (x, y, x + w, y + h), radius=radius, outline=border,
            width=max(2, h // 220),
        )
        img.alpha_composite(layer)


def _ring(
    img: Image.Image, x: int, y: int, w: int, h: int, radius: int,
    color: tuple[int, int, int], width: int = 4,
) -> None:
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(
        (x, y, x + w, y + h), radius=radius, outline=(*color, 255), width=width,
    )
    img.alpha_composite(layer)


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


def _draw_spaced(
    d: ImageDraw.ImageDraw, xy: tuple[int, int], text: str,
    font: ImageFont.FreeTypeFont, fill, *, spacing: int = 4, anchor: str = "lm",
) -> None:
    """Harflar orasiga bo'sh joy qo'yib yozadi (uppercase label uchun)."""
    x, y = xy
    widths = [d.textlength(ch, font=font) for ch in text]
    total = sum(widths) + spacing * (len(text) - 1)
    if anchor and anchor[0] == "m":
        x -= total / 2
    cx = x
    for ch, w in zip(text, widths, strict=True):
        d.text((cx, y), ch, font=font, fill=fill, anchor="lm")
        cx += w + spacing


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
    """v8: Kunduzgi (light) islomiy — hero + 2x3 grid, supersample HD."""
    settings = get_settings()
    out_w, out_h = size
    S = SS
    W, H = out_w * S, out_h * S  # ichkarida SS barobar katta render

    home = _normalize_times(region_times)
    mosq = _normalize_times(masjid_times)

    has_mosq = any(mosq.get(p) for p in ALL_PRAYERS)
    if has_mosq:
        _apply_fallback(home, mosq)

    img = _make_bg(W, H)

    # ── Masjidul Aqso motivi — header markazidagi bo'sh joyda, ixcham ────
    motif_w = int(0.30 * W)
    motif_h = int(0.115 * H)
    motif = aqsa_backdrop(width=motif_w, height=motif_h, color=COLOR_GOLD, alpha=75)
    img.alpha_composite(
        motif, (W // 2 - motif_w // 2, int(0.140 * H) - motif_h),
    )

    # ── Premium ikki qavat oltin hoshiya ──────────────────────────────────
    frame = Image.new("RGBA", img.size, (0, 0, 0, 0))
    fd = ImageDraw.Draw(frame)
    m1 = int(0.018 * W)
    fd.rounded_rectangle(
        (m1, m1, W - m1, H - m1),
        radius=int(0.030 * W), outline=(*COLOR_GOLD, 140), width=3 * S,
    )
    m2 = m1 + 10 * S
    fd.rounded_rectangle(
        (m2, m2, W - m2, H - m2),
        radius=int(0.026 * W), outline=(*COLOR_GOLD, 70), width=1 * S,
    )
    img.alpha_composite(frame)

    d = ImageDraw.Draw(img)

    # ============== Fontlar ==============
    f_region = _load_font(FONT_FILES["title"], int(0.052 * H))
    _try_variant(f_region, "Bold")
    f_label = _load_font(FONT_FILES["subtitle"], int(0.018 * H))
    _try_variant(f_label, "SemiBold")
    f_date = _load_font(FONT_FILES["subtitle"], int(0.024 * H))
    _try_variant(f_date, "SemiBold")
    f_date_dim = _load_font(FONT_FILES["subtitle"], int(0.021 * H))
    _try_variant(f_date_dim, "Medium")

    f_hero_label = _load_font(FONT_FILES["subtitle"], int(0.020 * H))
    _try_variant(f_hero_label, "Bold")
    f_hero_name = _load_font(FONT_FILES["name"], int(0.040 * H))
    _try_variant(f_hero_name, "Bold")
    f_hero_time = _load_font(FONT_FILES["time"], int(0.115 * H))
    _try_variant(f_hero_time, "Bold")
    f_hero_sub = _load_font(FONT_FILES["subtitle"], int(0.022 * H))
    _try_variant(f_hero_sub, "SemiBold")

    f_card_name = _load_font(FONT_FILES["name"], int(0.023 * H))
    _try_variant(f_card_name, "Bold")
    f_card_time = _load_font(FONT_FILES["time"], int(0.046 * H))
    _try_variant(f_card_time, "Bold")
    f_card_jamoat = _load_font(FONT_FILES["subtitle"], int(0.0165 * H))
    _try_variant(f_card_jamoat, "Medium")

    f_footer = _load_font(FONT_FILES["subtitle"], int(0.019 * H))
    _try_variant(f_footer, "Medium")

    margin = int(0.052 * W)

    # ============== Header ==============
    region_y = int(0.082 * H)
    pin = _load_emoji("round_pushpin.png", int(0.044 * H))
    rx = margin
    if pin:
        img.alpha_composite(pin, (rx, region_y - pin.size[1] // 2))
        rx += pin.size[0] + 12 * S
    d.text(
        (rx, region_y), region_name.upper(),
        font=f_region, fill=COLOR_GOLD, anchor="lm",
    )
    _draw_spaced(
        d, (margin + 2 * S, int(0.122 * H)), "NAMOZ VAQTLARI",
        f_label, COLOR_DIM, spacing=4 * S,
    )

    # Sanalar — o'ng tomonda
    d.text(
        (W - margin, int(0.078 * H)), milodiy,
        font=f_date, fill=COLOR_INK, anchor="rm",
    )
    d.text(
        (W - margin, int(0.116 * H)), hijriy,
        font=f_date_dim, fill=COLOR_DIM, anchor="rm",
    )

    # Nozik oltin ajratuvchi chiziq + markazda romb aksent
    line_y = int(0.155 * H)
    line = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld_ = ImageDraw.Draw(line)
    dia = 7 * S
    ld_.line(
        (margin, line_y, W // 2 - dia - 8 * S, line_y), fill=(*COLOR_GOLD, 120), width=2 * S,
    )
    ld_.line(
        (W // 2 + dia + 8 * S, line_y, W - margin, line_y), fill=(*COLOR_GOLD, 120), width=2 * S,
    )
    ld_.polygon(
        [
            (W // 2, line_y - dia), (W // 2 + dia, line_y),
            (W // 2, line_y + dia), (W // 2 - dia, line_y),
        ],
        fill=(*COLOR_GOLD, 200),
    )
    img.alpha_composite(line)

    # ============== HERO card (next prayer) ==============
    hero_prayer = _next_prayer(home, highlight_prayer)
    accent = COLOR_ACCENT.get(hero_prayer, (120, 130, 160))
    accent_dark = COLOR_ACCENT_DARK.get(hero_prayer, (70, 80, 110))

    hero_x = margin
    hero_y = int(0.185 * H)
    hero_w = W - 2 * margin
    hero_h = int(0.245 * H)
    hero_radius = int(0.034 * W)

    # Aksent nur (glow) hero ortida — chuqurlik uchun
    hglow = _radial_glow(int(hero_w * 1.1), accent, 70)
    img.alpha_composite(
        hglow,
        (hero_x + hero_w // 2 - hglow.size[0] // 2,
         hero_y + hero_h // 2 - hglow.size[1] // 2),
    )

    hero_fill = _make_vgradient(hero_w, hero_h, accent, accent_dark)
    _surface(img, hero_x, hero_y, hero_w, hero_h, hero_radius,
             fill=hero_fill, border=(255, 255, 255, 55))

    # Emoji chap
    hero_em_size = int(hero_h * 0.66)
    hero_em = _load_emoji(EMOJI_FILES.get(hero_prayer, ""), hero_em_size)
    if hero_em:
        ex = hero_x + int(hero_w * 0.055)
        ey = hero_y + (hero_h - hero_em.size[1]) // 2
        img.alpha_composite(hero_em, (ex, ey))

    tx = hero_x + int(hero_w * 0.34)
    label_text = "KEYINGI NAMOZ" if hero_prayer == highlight_prayer else "BUGUNGI NAMOZ"
    _draw_spaced(
        d, (tx, hero_y + int(hero_h * 0.22)), label_text,
        f_hero_label, (255, 255, 255, 215), spacing=3,
    )
    d.text(
        (tx, hero_y + int(hero_h * 0.40)), hero_prayer,
        font=f_hero_name, fill=COLOR_WHITE, anchor="lm",
    )
    time_y = hero_y + int(hero_h * 0.70)
    d.text(
        (tx, time_y), home.get(hero_prayer) or EMPTY_MARK,
        font=f_hero_time, fill=COLOR_WHITE, anchor="lm",
    )
    if has_mosq and mosq.get(hero_prayer):
        time_w = d.textlength(home.get(hero_prayer) or EMPTY_MARK, font=f_hero_time)
        d.text(
            (tx + time_w + 22 * S, time_y + int(hero_h * 0.06)),
            f"jamoat {mosq.get(hero_prayer)}",
            font=f_hero_sub, fill=(255, 255, 255, 215), anchor="lm",
        )

    # ============== 2x3 grid — barcha 6 namoz ==============
    grid_top = int(0.470 * H)
    grid_bottom = int(0.935 * H)
    cols, rows = 3, 2
    gap = int(0.020 * W)
    card_radius = int(0.026 * W)

    grid_w = W - 2 * margin
    card_w = (grid_w - gap * (cols - 1)) // cols
    card_h = (grid_bottom - grid_top - gap * (rows - 1)) // rows

    for idx, prayer in enumerate(ALL_PRAYERS):
        row, col = divmod(idx, cols)
        cx0 = margin + col * (card_w + gap)
        cy0 = grid_top + row * (card_h + gap)
        is_next = (prayer == highlight_prayer)
        p_accent = COLOR_ACCENT.get(prayer, (120, 130, 160))
        p_accent_dk = COLOR_ACCENT_DARK.get(prayer, (70, 80, 110))

        if is_next:
            # Keyingi namoz: yengil aksent tint + to'q aksent halqa
            tint = Image.new("RGBA", (card_w, card_h), (*p_accent, 30))
            base = Image.new("RGBA", (card_w, card_h), (*COLOR_SURFACE, 255))
            fill_img = Image.alpha_composite(base, tint)
            _surface(img, cx0, cy0, card_w, card_h, card_radius,
                     fill=fill_img, border=None)
            _ring(img, cx0, cy0, card_w, card_h, card_radius, p_accent_dk,
                  width=3 * S)
        else:
            _surface(img, cx0, cy0, card_w, card_h, card_radius)

        ccx = cx0 + card_w // 2

        em_size = int(card_h * 0.36)
        em = _load_emoji(EMOJI_FILES.get(prayer, ""), em_size)
        if em:
            img.alpha_composite(
                em, (ccx - em.size[0] // 2, cy0 + int(card_h * 0.10)),
            )

        # Kart nomi — to'q aksent (oq kartda kontrast uchun)
        d.text(
            (ccx, cy0 + int(card_h * 0.555)), prayer,
            font=f_card_name, fill=p_accent_dk, anchor="mm",
        )
        jamoat = mosq.get(prayer) if has_mosq else None
        time_yy = cy0 + int(card_h * (0.74 if jamoat else 0.80))
        d.text(
            (ccx, time_yy), home.get(prayer) or EMPTY_MARK,
            font=f_card_time, fill=COLOR_INK, anchor="mm",
        )
        if jamoat:
            d.text(
                (ccx, cy0 + int(card_h * 0.91)),
                f"jamoat {jamoat}",
                font=f_card_jamoat, fill=COLOR_GOLD, anchor="mm",
            )

    # ============== Footer ==============
    attribution = (
        "islomapi.uz · O'zbekiston musulmonlari idorasi"
        if has_mosq
        else "Aladhan API · ISNA · Hanafiy mazhab"
    )
    d.text(
        (W // 2, int(0.965 * H)), attribution,
        font=f_footer, fill=COLOR_DIM, anchor="mm",
    )

    # ============== Saqlash ==============
    if out_filename:
        out_path = settings.images_dir / out_filename
    else:
        out_path = settings.images_dir / f"{_safe_filename(region_name)}.png"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Supersample'ni yakuniy o'lchamga LANCZOS bilan kichraytirish (crisp) +
    # PNG lossless — send_photo qayta siqadi, lekin manba maksimal toza bo'ladi.
    final = img.convert("RGB").resize((out_w, out_h), Image.Resampling.LANCZOS)
    final.save(out_path, format="PNG", optimize=True)
    logger.debug("Rasm saqlandi: {} ({}x{})", out_path, out_w, out_h)
    return out_path


__all__ = ["make_prayer_image"]
