"""Qashqadaryo viloyati — kunlik namoz vaqtlari posteri.

v7 — Zamonaviy iOS islomiy dizayn (2x HD):
  * Chuqur to'q yashil-charcoal gradient fon + yumshoq nur (glow)
  * iOS "grouped table" karti: yumaloq burchak, hairline ajratuvchilar
  * To'yingan rang bloklari o'rniga — neytral hujayralar + rangli ustun aksenti
  * Oltin sarlavha, kaaba ikoni, iOS pill ko'rinishidagi sana
  * Masjid vaqtlari — alohida oltin-tint sub-kart
  * Nafis tipografika, ko'p bo'sh joy, premium his
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from app.core.config import get_settings
from app.core.logger import logger
from app.services.backdrop import aqsa_backdrop
from app.utils.time_utils import clean_hhmm

# ── Canvas ────────────────────────────────────────────────────────────────────
SCALE: int = 2                                      # 2x → HD
DEFAULT_SIZE: tuple[int, int] = (1080 * SCALE, 1952 * SCALE)

# ── Fonts ─────────────────────────────────────────────────────────────────────
FONT_FILES: dict[str, str] = {
    "title":    "Montserrat-VariableFont_wght.ttf",
    "row":      "Nunito-VariableFont_wght.ttf",
    "time":     "Manrope-VariableFont_wght.ttf",
    "fallback": "NotoSans-VariableFont_wdth,wght.ttf",
}

# ── Tuman order ───────────────────────────────────────────────────────────────
TUMAN_ORDER_CYR: list[tuple[str, str]] = [
    ("Qarshi",      "ҚАРШИ"),
    ("Dehqonobod",  "ДЕҲҚОНОБОД"),
    ("G'uzor",      "ҒУЗОР"),
    ("Kasbi",       "КАСБИ"),
    ("Kitob",       "КИТОБ"),
    ("Koson",       "КОСОН"),
    ("Mirishkor",   "МИРИШКОР"),
    ("Muborak",     "МУБОРАК"),
    ("Nishon",      "НИШОН"),
    ("Qamashi",     "ҚАМАШИ"),
    ("Shahrisabz",  "ШАҲРИСАБЗ"),
    ("Yakkabog'",   "ЯККАБОҒ"),
    ("Chiroqchi",   "ЧИРОҚЧИ"),
    ("Ko'kdala",    "КЎКДАЛА"),
]

CYR_MONTHS: dict[int, str] = {
    1: "ЯНВАР", 2: "ФЕВРАЛ", 3: "МАРТ", 4: "АПРЕЛ",
    5: "МАЙ",   6: "ИЮН",    7: "ИЮЛ",  8: "АВГУСТ",
    9: "СЕНТЯБР", 10: "ОКТЯБР", 11: "НОЯБР", 12: "ДЕКАБР",
}

# ── Prayer columns (iOS aksent — och fonda "accent_dk" ishlatiladi) ────────────
PRAYER_COLUMNS: list[dict] = [
    {"key": "Bomdod", "cyr": "БОМДОД", "accent": (96, 170, 255),  "accent_dk": (44, 104, 182), "icon": "cityscape_dusk.png"},
    {"key": "Quyosh", "cyr": "ҚУЁШ",   "accent": (255, 201, 102), "accent_dk": (188, 138, 40), "icon": "sunrise.png"},
    {"key": "Peshin", "cyr": "ПЕШИН",  "accent": (255, 128, 99),  "accent_dk": (196, 70, 50),  "icon": "sun_face.png"},
    {"key": "Asr",    "cyr": "АСР",    "accent": (255, 168, 82),  "accent_dk": (188, 110, 32), "icon": "sun_cloud.png"},
    {"key": "Shom",   "cyr": "ШОМ",    "accent": (236, 124, 162), "accent_dk": (170, 62, 104), "icon": "sunset.png"},
    {"key": "Xufton", "cyr": "ХУФТОН", "accent": (146, 138, 238), "accent_dk": (82, 72, 178),  "icon": "moon.png"},
]

# ── Colors (kunduzgi / light) ──────────────────────────────────────────────────
COLOR_BG_TOP    = (252, 250, 245)     # issiq oq (cream)
COLOR_BG_BOT    = (236, 242, 236)     # och yashil-kul
COLOR_GLOW      = (208, 224, 210)     # header ortida yumshoq nur

COLOR_GOLD      = (176, 138, 58)      # to'q oltin (och fonda)
COLOR_GOLD_DK   = (140, 106, 42)
COLOR_WHITE     = (255, 255, 255)
COLOR_INK       = (30, 48, 40)        # asosiy to'q matn
COLOR_DIM       = (112, 126, 116)     # ikkilamchi

COLOR_COLHDR_BG = (236, 240, 233)     # och col-header
COLOR_ROW_A     = (255, 255, 255)     # juft satr — oq
COLOR_ROW_B     = (246, 249, 245)     # toq satr — juda och
COLOR_SEP       = (22, 46, 34, 28)    # to'q hairline
COLOR_GOLD_SEP  = (176, 138, 58, 95)
COLOR_MASJID_BG = (250, 244, 229)     # issiq oltin-tint sub-kart
COLOR_BORDER    = (22, 46, 34, 45)

COLOR_DATE_FG   = (255, 251, 244)     # oltin pill ichidagi och matn
COLOR_FOOTER_FG = (120, 134, 124)
COLOR_TEST_FG   = (200, 58, 66)
COLOR_SHADOW    = (26, 46, 36)        # kart ostidagi yumshoq soya

EMPTY_MARK = "—"


# ── Drawing helpers ───────────────────────────────────────────────────────────

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
    if not (hasattr(font, "get_variation_names") and hasattr(font, "set_variation_by_name")):
        return
    try:
        names = font.get_variation_names()
        low = [n.lower() for n in names]
        for key in (want.lower(), "bold", "semibold", "regular"):
            if key in low:
                font.set_variation_by_name(names[low.index(key)])
                return
    except OSError as e:
        logger.debug("Font variant qo'yilmadi: {}", e)


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


def _safe_filename(s: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", s).strip("_")
    return cleaned or "table"


def _normalize_row(row: dict[str, str] | None) -> dict[str, str]:
    if not row:
        return {}
    return {k: (clean_hhmm(v) or "") for k, v in row.items()}


def _vgrad(
    img: Image.Image,
    xy: tuple[int, int, int, int],
    c_top: tuple[int, int, int],
    c_bot: tuple[int, int, int],
) -> None:
    """Vertical gradient (top→bottom) to'g'ridan img ustiga."""
    x1, y1, x2, y2 = xy
    h = y2 - y1
    if h <= 0:
        return
    band = Image.new("RGB", (1, h))
    for i in range(h):
        t = i / max(h - 1, 1)
        band.putpixel((0, i), (
            int(c_top[0] + (c_bot[0] - c_top[0]) * t),
            int(c_top[1] + (c_bot[1] - c_top[1]) * t),
            int(c_top[2] + (c_bot[2] - c_top[2]) * t),
        ))
    img.paste(band.resize((x2 - x1, h)), (x1, y1))


def _hgrad(
    w: int, h: int,
    c_l: tuple[int, int, int], c_r: tuple[int, int, int],
) -> Image.Image:
    band = Image.new("RGB", (w, 1))
    for col in range(w):
        t = col / max(w - 1, 1)
        band.putpixel((col, 0), (
            int(c_l[0] + (c_r[0] - c_l[0]) * t),
            int(c_l[1] + (c_r[1] - c_l[1]) * t),
            int(c_l[2] + (c_r[2] - c_l[2]) * t),
        ))
    return band.resize((w, h)).convert("RGBA")


def _radial_glow(diam: int, color: tuple[int, int, int], max_alpha: int) -> Image.Image:
    grad = Image.radial_gradient("L").resize((diam, diam))   # 0 markaz → 255 chet
    alpha = ImageOps.invert(grad).point(lambda v: int((v / 255) * max_alpha))
    layer = Image.new("RGBA", (diam, diam), (*color, 0))
    layer.putalpha(alpha)
    return layer


def _rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return mask


def _text_tracked(
    d: ImageDraw.ImageDraw, xy: tuple[int, int], text: str,
    font: ImageFont.FreeTypeFont, fill, *, tracking: int = 0, anchor: str = "mm",
) -> None:
    """Harf oralig'i (letter-spacing) bilan markazga joylab yozadi."""
    if tracking == 0:
        d.text(xy, text, font=font, fill=fill, anchor=anchor)
        return
    widths = [d.textlength(ch, font=font) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = xy[0] - total / 2
    for ch, w in zip(text, widths, strict=True):
        d.text((x, xy[1]), ch, font=font, fill=fill, anchor="lm")
        x += w + tracking


# ── Public API ────────────────────────────────────────────────────────────────

def render_qashqadaryo_table(
    *,
    target_date: date,
    regions_data: dict[str, dict[str, str]],
    masjid_times: dict[str, str] | None = None,
    test_mode: bool = False,
    out_filename: str | None = None,
) -> Path:
    """iOS islomiy premium dizayn: to'q fon, grouped table karti, oltin aksent. 2x HD."""
    settings = get_settings()
    S = SCALE

    # ── Layout konstantalari (dizayn birligi, keyin × S) ──────────────────
    OUT       = 40 * S
    DECOR_TOP = 34 * S
    DECOR_H   = 168 * S
    TITLE_Y   = 248 * S
    SUB_Y     = 304 * S
    PILL_Y1   = 346 * S
    PILL_H    = 68 * S
    CARD_TOP  = 466 * S
    COLHDR_H  = 132 * S
    ROW_H     = 80 * S
    MASJID_H  = 176 * S
    RADIUS    = 40 * S

    n_rows = len(TUMAN_ORDER_CYR)
    card_h = COLHDR_H + n_rows * ROW_H + MASJID_H
    card_bottom = CARD_TOP + card_h
    foot_y = card_bottom + 46 * S

    W = 1080 * S
    H = foot_y + 110 * S

    # ── Canvas + fon ──────────────────────────────────────────────────────
    img = Image.new("RGBA", (W, H), (*COLOR_BG_BOT, 255))
    _vgrad(img, (0, 0, W, H), COLOR_BG_TOP, COLOR_BG_BOT)

    # Header ortida yumshoq nur
    glow = _radial_glow(900 * S, COLOR_GLOW, 70)
    img.alpha_composite(glow, (W // 2 - glow.size[0] // 2, -260 * S))

    # ── Masjidul Aqso motivi — sarlavha tepasida, alohida dekor zona ─────
    decor_w = int(W * 0.58)
    decor = aqsa_backdrop(width=decor_w, height=DECOR_H, color=COLOR_GOLD, alpha=80)
    img.alpha_composite(decor, (W // 2 - decor_w // 2, DECOR_TOP))

    # ── Premium ikki qavat oltin hoshiya ──────────────────────────────────
    frame = Image.new("RGBA", img.size, (0, 0, 0, 0))
    fd = ImageDraw.Draw(frame)
    fd.rounded_rectangle(
        (16 * S, 16 * S, W - 16 * S, H - 16 * S),
        radius=34 * S, outline=(*COLOR_GOLD, 150), width=2 * S,
    )
    fd.rounded_rectangle(
        (25 * S, 25 * S, W - 25 * S, H - 25 * S),
        radius=30 * S, outline=(*COLOR_GOLD, 70), width=1 * S,
    )
    img.alpha_composite(frame)

    d = ImageDraw.Draw(img)

    # ── Fonts ─────────────────────────────────────────────────────────────
    f_title   = _load_font(FONT_FILES["title"], 50 * S); _try_variant(f_title, "Bold")
    f_sub     = _load_font(FONT_FILES["title"], 26 * S); _try_variant(f_sub, "Medium")
    f_date    = _load_font(FONT_FILES["title"], 29 * S); _try_variant(f_date, "Bold")
    f_col     = _load_font(FONT_FILES["title"], 22 * S); _try_variant(f_col, "Bold")
    f_thdr    = _load_font(FONT_FILES["title"], 21 * S); _try_variant(f_thdr, "Bold")
    f_tuman   = _load_font(FONT_FILES["row"],   21 * S); _try_variant(f_tuman, "Bold")
    f_time    = _load_font(FONT_FILES["time"],  33 * S); _try_variant(f_time, "Bold")
    f_mlbl    = _load_font(FONT_FILES["row"],   19 * S); _try_variant(f_mlbl, "Bold")
    f_mtime   = _load_font(FONT_FILES["time"],  31 * S); _try_variant(f_mtime, "Bold")
    f_footer  = _load_font(FONT_FILES["row"],   20 * S); _try_variant(f_footer, "Medium")
    f_test    = _load_font(FONT_FILES["row"],   20 * S); _try_variant(f_test, "Bold")

    # ── HEADER ────────────────────────────────────────────────────────────
    _text_tracked(
        d, (W // 2, TITLE_Y), "ҚАШҚАДАРЁ ВИЛОЯТИ",
        f_title, COLOR_GOLD, tracking=4 * S, anchor="mm",
    )
    _text_tracked(
        d, (W // 2, SUB_Y), "Кунлик намоз вақтлари",
        f_sub, COLOR_DIM, tracking=2 * S, anchor="mm",
    )

    # Sana — iOS pill (oltin gradient, to'q matn)
    cyr_month = CYR_MONTHS.get(target_date.month, str(target_date.month))
    date_text = f"{target_date.day}-{cyr_month} {target_date.year}"
    dt_w = d.textlength(date_text, font=f_date)
    pill_w = int(dt_w + 64 * S)
    pill_x1 = W // 2 - pill_w // 2
    pill = _hgrad(pill_w, PILL_H, COLOR_GOLD, COLOR_GOLD_DK)
    pill.putalpha(_rounded_mask((pill_w, PILL_H), PILL_H // 2))
    img.alpha_composite(pill, (pill_x1, PILL_Y1))
    d = ImageDraw.Draw(img)
    d.text((W // 2, PILL_Y1 + PILL_H // 2), date_text,
           font=f_date, fill=COLOR_DATE_FG, anchor="mm")

    # ── TABLE CARD (alohida layerda, keyin yumaloq mask) ──────────────────
    card_x1 = OUT
    card_x2 = W - OUT
    card_w = card_x2 - card_x1

    prayer_w = (card_w - 164 * S) // 6
    tuman_w = card_w - 6 * prayer_w

    layer = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)

    # Surface'lar: colhdr, alternating rows, masjid
    ld.rectangle((0, 0, card_w, COLHDR_H), fill=(*COLOR_COLHDR_BG, 255))
    for r in range(n_rows):
        ry1 = COLHDR_H + r * ROW_H
        fill = COLOR_ROW_B if r % 2 else COLOR_ROW_A
        ld.rectangle((0, ry1, card_w, ry1 + ROW_H), fill=(*fill, 255))
    msj_y1 = COLHDR_H + n_rows * ROW_H
    ld.rectangle((0, msj_y1, card_w, card_h), fill=(*COLOR_MASJID_BG, 255))

    # ── Column headers ────────────────────────────────────────────────────
    pin = _load_emoji("round_pushpin.png", 52 * S)
    if pin:
        layer.paste(pin, (tuman_w // 2 - pin.size[0] // 2, 24 * S), pin)
        ld = ImageDraw.Draw(layer)
    ld.text((tuman_w // 2, COLHDR_H - 30 * S), "ТУМАНЛАР",
            font=f_thdr, fill=COLOR_GOLD, anchor="mm")

    for i, col in enumerate(PRAYER_COLUMNS):
        cx1 = tuman_w + i * prayer_w
        cx_mid = cx1 + prayer_w // 2
        accent_dk = col["accent_dk"]
        icon = _load_emoji(col["icon"], 70 * S)
        if icon:
            layer.paste(icon, (cx_mid - icon.size[0] // 2, 16 * S), icon)
            ld = ImageDraw.Draw(layer)
        ld.text((cx_mid, COLHDR_H - 50 * S), col["cyr"],
                font=f_col, fill=accent_dk, anchor="mm")
        # Nozik aksent chizig'i (underline) — och fonda to'q variant
        uw = int(prayer_w * 0.34)
        ld.line((cx_mid - uw // 2, COLHDR_H - 22 * S, cx_mid + uw // 2, COLHDR_H - 22 * S),
                fill=(*accent_dk, 255), width=3 * S)

    # ── Data rows ─────────────────────────────────────────────────────────
    for r, (lotin, cyr) in enumerate(TUMAN_ORDER_CYR):
        ry1 = COLHDR_H + r * ROW_H
        ry_mid = ry1 + ROW_H // 2
        row_data = _normalize_row(regions_data.get(lotin))
        has_data = any(row_data.get(col["key"]) for col in PRAYER_COLUMNS)

        ld.text((tuman_w // 2, ry_mid), cyr,
                font=f_tuman, fill=COLOR_INK, anchor="mm")

        for i, col in enumerate(PRAYER_COLUMNS):
            cx_mid = tuman_w + i * prayer_w + prayer_w // 2
            t = row_data.get(col["key"]) or ""
            if t:
                ld.text((cx_mid, ry_mid), t, font=f_time, fill=COLOR_INK, anchor="mm")
            elif not has_data:
                ld.text((cx_mid, ry_mid), EMPTY_MARK,
                        font=f_time, fill=(*COLOR_DIM, 160), anchor="mm")

        # Hairline (satrlar orasida)
        if r < n_rows - 1:
            ld.line((24 * S, ry1 + ROW_H, card_w - 24 * S, ry1 + ROW_H),
                    fill=COLOR_SEP, width=1 * S)

    # ── Masjid sub-card ───────────────────────────────────────────────────
    mosq = _normalize_row(masjid_times or {})
    ld.line((0, msj_y1, card_w, msj_y1), fill=COLOR_GOLD_SEP, width=2 * S)

    msj_mid = msj_y1 + MASJID_H // 2
    for idx, line in enumerate(("МАСЖИД", "вақтлари")):
        ld.text((tuman_w // 2, msj_mid - 16 * S + idx * 36 * S),
                line, font=f_mlbl, fill=COLOR_GOLD, anchor="mm")

    for i, col in enumerate(PRAYER_COLUMNS):
        cx_mid = tuman_w + i * prayer_w + prayer_w // 2
        if col["key"] == "Quyosh":
            ld.text((cx_mid, msj_mid), EMPTY_MARK,
                    font=f_mtime, fill=(*COLOR_GOLD_DK, 150), anchor="mm")
            continue
        t = mosq.get(col["key"]) or EMPTY_MARK
        ld.text((cx_mid, msj_mid), t, font=f_mtime, fill=COLOR_GOLD, anchor="mm")

    # Tuman ↔ prayer ustunlari orasida nozik oltin ajratuvchi
    ld.line((tuman_w, 0, tuman_w, card_h), fill=COLOR_GOLD_SEP, width=2 * S)
    # Colhdr ↔ data ajratuvchi
    ld.line((0, COLHDR_H, card_w, COLHDR_H), fill=(22, 46, 34, 55), width=2 * S)

    # Kart ostida yumshoq soya (och fonda chuqurlik uchun)
    sh_pad = 30 * S
    shadow = Image.new("RGBA", (card_w + sh_pad * 2, card_h + sh_pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (sh_pad, sh_pad, sh_pad + card_w, sh_pad + card_h),
        radius=RADIUS, fill=(*COLOR_SHADOW, 60),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(18 * S))
    img.alpha_composite(shadow, (card_x1 - sh_pad, CARD_TOP - sh_pad + 8 * S))

    # Yumaloq mask + asosiy rasmga joylash (kart butun yuzasi to'ldirilgan)
    layer.putalpha(_rounded_mask((card_w, card_h), RADIUS))
    img.alpha_composite(layer, (card_x1, CARD_TOP))

    # Nozik hairline ramka
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(
        (card_x1, CARD_TOP, card_x2, card_bottom),
        radius=RADIUS, outline=COLOR_BORDER, width=1 * S,
    )

    # ── FOOTER ────────────────────────────────────────────────────────────
    d.text((W // 2, foot_y), "Ўзбекистон мусулмонлари идораси услуби бўйича",
           font=f_footer, fill=COLOR_FOOTER_FG, anchor="mm")
    if test_mode:
        d.text((W // 2, foot_y + 40 * S), "ТЕСТ РЕЖИМДА",
               font=f_test, fill=COLOR_TEST_FG, anchor="mm")

    # ── Save — lossless PNG ───────────────────────────────────────────────
    if out_filename:
        out_path = settings.images_dir / out_filename
    else:
        out_path = (
            settings.images_dir
            / f"qashqadaryo_table_{_safe_filename(target_date.isoformat())}.png"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(str(out_path), format="PNG", compress_level=1)
    logger.debug("Qashqadaryo table saqlandi ({}x{}): {}", W, H, out_path)
    return out_path


__all__ = [
    "PRAYER_COLUMNS",
    "TUMAN_ORDER_CYR",
    "render_qashqadaryo_table",
]
