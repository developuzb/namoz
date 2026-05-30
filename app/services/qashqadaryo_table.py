"""Qashqadaryo viloyati — premium dizayn v6 (2x HD), kunlik namoz vaqtlari posteri.

Tuzilish (v6 — 2x HD):
  * Canvas: 2160×4064 px (2x supersampling) — maksimal keskinlik
  * Toʻq yashil gradient header (kaaba ikoni, oltin sarlavha)
  * Gradient ustun sarlavhalari (qoʻyu → yorqin)
  * Alternating row shading
  * Gradient sana banneri, yumaloq burchaklar
  * Oltin accent, chiziqlar, ajratuvchilar
  * PNG lossless, compress_level=1 (eng yuqori sifat)
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.core.config import get_settings
from app.core.logger import logger
from app.utils.time_utils import clean_hhmm

# ── Canvas ────────────────────────────────────────────────────────────────────
SCALE: int = 2                                      # 2x supersampling → HD
DEFAULT_SIZE: tuple[int, int] = (1080 * SCALE, 2032 * SCALE)
_M = 24 * SCALE  # margin

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

# ── Prayer columns ────────────────────────────────────────────────────────────
PRAYER_COLUMNS: list[dict] = [
    {
        "key": "Bomdod",  "cyr": "БОМДОД",
        "color":      (38, 98, 175),
        "color_dark": (22, 62, 125),
        "subtitle": "(Азон\nайтилиш\nвақти)",
        "icon": "cityscape_dusk.png",
    },
    {
        "key": "Quyosh",  "cyr": "ҚУЁШ",
        "color":      (155, 118, 12),
        "color_dark": (108, 80, 8),
        "subtitle": "(Бомдод\nтугаши\nвақти)",
        "icon": "sunrise.png",
    },
    {
        "key": "Peshin",  "cyr": "ПЕШИН",
        "color":      (185, 60, 38),
        "color_dark": (132, 38, 22),
        "subtitle": "(Кириш\nвақти)",
        "icon": "sun_face.png",
    },
    {
        "key": "Asr",     "cyr": "АСР",
        "color":      (198, 108, 32),
        "color_dark": (142, 72, 18),
        "subtitle": "(Азон\nвақти)",
        "icon": "sun_cloud.png",
    },
    {
        "key": "Shom",    "cyr": "ШОМ",
        "color":      (60, 78, 105),
        "color_dark": (38, 54, 78),
        "subtitle": "(Азон\nвақти)",
        "icon": "sunset.png",
    },
    {
        "key": "Xufton",  "cyr": "ХУФТОН",
        "color":      (82, 72, 65),
        "color_dark": (52, 45, 40),
        "subtitle": "(Азон\nвақти)",
        "icon": "moon.png",
    },
]

# ── Colors ────────────────────────────────────────────────────────────────────
COLOR_PAGE_BG    = (244, 242, 238)

COLOR_HDR_TOP    = (8, 36, 22)
COLOR_HDR_BOT    = (22, 75, 47)
COLOR_HDR_WHITE  = (255, 255, 255)
COLOR_HDR_GOLD   = (218, 172, 68)

COLOR_FRAME      = (16, 58, 36)
COLOR_GRID       = (255, 255, 255)
COLOR_TUMAN_FG   = (255, 255, 255)
COLOR_TUMAN_LBL  = (218, 172, 68)

COLOR_TIME_FG    = (255, 255, 255)
COLOR_SUB_FG     = (255, 250, 238)
COLOR_NAME_FG    = (255, 255, 255)

COLOR_MASJID_HDR = (172, 108, 22)
COLOR_MASJID_FG  = (255, 255, 255)

COLOR_DATE_L     = (155, 20, 28)
COLOR_DATE_R     = (198, 50, 60)
COLOR_DATE_FG    = (255, 248, 215)

COLOR_FOOTER_FG  = (88, 82, 70)
COLOR_TEST_FG    = (185, 32, 42)

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
    """Vertical gradient (top→bottom) directly onto img."""
    x1, y1, x2, y2 = xy
    h = y2 - y1
    if h <= 0:
        return
    d = ImageDraw.Draw(img)
    for i in range(h):
        t = i / max(h - 1, 1)
        color = (
            int(c_top[0] + (c_bot[0] - c_top[0]) * t),
            int(c_top[1] + (c_bot[1] - c_top[1]) * t),
            int(c_top[2] + (c_bot[2] - c_top[2]) * t),
            255,
        )
        d.line((x1, y1 + i, x2, y1 + i), fill=color)


def _hgrad_rounded(
    img: Image.Image,
    xy: tuple[int, int, int, int],
    c_l: tuple[int, int, int],
    c_r: tuple[int, int, int],
    radius: int = 10,
) -> None:
    """Horizontal gradient with rounded corners composited onto img."""
    x1, y1, x2, y2 = xy
    w, h = x2 - x1, y2 - y1
    if w <= 0 or h <= 0:
        return
    band = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    for col in range(w):
        t = col / max(w - 1, 1)
        color = (
            int(c_l[0] + (c_r[0] - c_l[0]) * t),
            int(c_l[1] + (c_r[1] - c_l[1]) * t),
            int(c_l[2] + (c_r[2] - c_l[2]) * t),
            255,
        )
        bd.line((col, 0, col, h - 1), fill=color)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    band.putalpha(mask)
    img.alpha_composite(band, (x1, y1))


def _lighten(c: tuple[int, int, int], f: float) -> tuple[int, int, int]:
    return (
        min(255, int(c[0] + (255 - c[0]) * f)),
        min(255, int(c[1] + (255 - c[1]) * f)),
        min(255, int(c[2] + (255 - c[2]) * f)),
    )


# ── Public API ────────────────────────────────────────────────────────────────

def render_qashqadaryo_table(
    *,
    target_date: date,
    regions_data: dict[str, dict[str, str]],
    masjid_times: dict[str, str] | None = None,
    test_mode: bool = False,
    out_filename: str | None = None,
) -> Path:
    """Premium dizayn: gradient header, oltin aksentlar, alternating rows. 2x HD."""
    settings = get_settings()
    S = SCALE
    W, H = DEFAULT_SIZE

    img = Image.new("RGBA", (W, H), COLOR_PAGE_BG + (255,))

    # ── Fonts (all sizes × S) ─────────────────────────────────────────────
    f_hdr_sub  = _load_font(FONT_FILES["title"], 29 * S);  _try_variant(f_hdr_sub,  "SemiBold")
    f_hdr_main = _load_font(FONT_FILES["title"], 56 * S);  _try_variant(f_hdr_main, "Bold")
    f_hdr_sub2 = _load_font(FONT_FILES["title"], 31 * S);  _try_variant(f_hdr_sub2, "Bold")

    f_col_name  = _load_font(FONT_FILES["title"], 24 * S); _try_variant(f_col_name,  "Bold")
    f_col_sub   = _load_font(FONT_FILES["row"],   19 * S); _try_variant(f_col_sub,   "Bold")
    f_tuman_lbl = _load_font(FONT_FILES["title"], 24 * S); _try_variant(f_tuman_lbl, "Bold")
    f_tuman_nm  = _load_font(FONT_FILES["row"],   22 * S); _try_variant(f_tuman_nm,  "Bold")
    f_time      = _load_font(FONT_FILES["time"],  38 * S); _try_variant(f_time,      "Bold")
    f_masjid_h  = _load_font(FONT_FILES["row"],   22 * S); _try_variant(f_masjid_h,  "Bold")
    f_masjid_t  = _load_font(FONT_FILES["time"],  30 * S); _try_variant(f_masjid_t,  "Bold")
    f_date      = _load_font(FONT_FILES["title"], 46 * S); _try_variant(f_date,      "Bold")
    f_footer    = _load_font(FONT_FILES["row"],   21 * S); _try_variant(f_footer,    "SemiBold")
    f_test      = _load_font(FONT_FILES["row"],   22 * S); _try_variant(f_test,      "Bold")

    # ── HEADER BANNER ─────────────────────────────────────────────────────
    HDR_H = 278 * S
    _vgrad(img, (0, 0, W, HDR_H), COLOR_HDR_TOP, COLOR_HDR_BOT)

    d = ImageDraw.Draw(img)
    d.line((60*S, 15*S, W - 60*S, 15*S), fill=COLOR_HDR_GOLD, width=2*S)

    kaaba = _load_emoji("kaaba.png", 92 * S)
    if kaaba:
        img.paste(kaaba, (W // 2 - kaaba.size[0] // 2, 24 * S), kaaba)
        d = ImageDraw.Draw(img)

    d.text((W // 2, 148 * S), "ҚАШҚАДАРЁ ВИЛОЯТИ БАРЧА ҲУДУДИ УЧУН",
           font=f_hdr_sub, fill=COLOR_HDR_GOLD, anchor="mm")
    d.text((W // 2, 200 * S), "«КУНЛИК НАМОЗ ВАҚТЛАРИ»",
           font=f_hdr_main, fill=COLOR_HDR_WHITE, anchor="mm")
    d.text((W // 2, 250 * S), "РЎЙХАТИ",
           font=f_hdr_sub2, fill=COLOR_HDR_GOLD, anchor="mm")
    d.line((60*S, HDR_H - 14*S, W - 60*S, HDR_H - 14*S), fill=COLOR_HDR_GOLD, width=2*S)

    # ── TABLE LAYOUT ──────────────────────────────────────────────────────
    table_top    = HDR_H + 18 * S
    table_left   = _M
    tuman_col_w  = 175 * S
    prayer_col_w = (W - 2 * _M - tuman_col_w) // 6
    table_right  = table_left + tuman_col_w + 6 * prayer_col_w

    HDR_ROW_H    = 260 * S
    DATA_ROW_H   = 78 * S
    MASJID_ROW_H = 120 * S
    n_rows = len(TUMAN_ORDER_CYR)

    table_bottom = table_top + HDR_ROW_H + n_rows * DATA_ROW_H + MASJID_ROW_H

    # Outer dark green frame
    d.rectangle((table_left, table_top, table_right, table_bottom), fill=COLOR_FRAME)

    # Gold vertical separator: tuman ↔ prayer columns
    sep_x = table_left + tuman_col_w
    d.line((sep_x, table_top, sep_x, table_bottom), fill=COLOR_HDR_GOLD, width=2*S)

    # ── COLUMN HEADERS ────────────────────────────────────────────────────
    hdr_y1 = table_top
    hdr_y2 = table_top + HDR_ROW_H

    # Tuman column header
    pin = _load_emoji("round_pushpin.png", 65 * S)
    if pin:
        img.paste(pin, (table_left + tuman_col_w // 2 - pin.size[0] // 2, hdr_y1 + 30*S), pin)
        d = ImageDraw.Draw(img)
    d.text(
        (table_left + tuman_col_w // 2, hdr_y2 - 30*S),
        "ТУМАНЛАР",
        font=f_tuman_lbl, fill=COLOR_TUMAN_LBL, anchor="mm",
    )

    # Prayer column headers
    for i, col in enumerate(PRAYER_COLUMNS):
        cx1 = table_left + tuman_col_w + i * prayer_col_w
        cx2 = cx1 + prayer_col_w
        cx_mid = (cx1 + cx2) // 2

        _vgrad(img, (cx1, hdr_y1, cx2, hdr_y2), col["color_dark"], col["color"])
        d = ImageDraw.Draw(img)

        icon = _load_emoji(col["icon"], 96 * S)
        if icon:
            img.paste(icon, (cx_mid - icon.size[0] // 2, hdr_y1 + 12*S), icon)
            d = ImageDraw.Draw(img)

        for li, line in enumerate(col["subtitle"].split("\n")):
            d.text(
                (cx_mid, hdr_y1 + 128*S + li * 24*S),
                line, font=f_col_sub, fill=COLOR_SUB_FG, anchor="mm",
            )

        # Prayer name bold at bottom of header
        d.text(
            (cx_mid, hdr_y2 - 24*S),
            col["cyr"], font=f_col_name, fill=COLOR_NAME_FG, anchor="mm",
        )

    # Header / data separator
    d.line((table_left, hdr_y2, table_right, hdr_y2), fill=COLOR_GRID, width=3*S)

    # ── DATA ROWS ─────────────────────────────────────────────────────────
    for r, (lotin, cyr) in enumerate(TUMAN_ORDER_CYR):
        ry1 = hdr_y2 + r * DATA_ROW_H
        ry2 = ry1 + DATA_ROW_H
        row_data = _normalize_row(regions_data.get(lotin))
        alt = r % 2 == 1

        d.text(
            (table_left + tuman_col_w // 2, (ry1 + ry2) // 2),
            cyr, font=f_tuman_nm, fill=COLOR_TUMAN_FG, anchor="mm",
        )

        has_data = any(row_data.get(col["key"]) for col in PRAYER_COLUMNS)

        for i, col in enumerate(PRAYER_COLUMNS):
            cx1 = table_left + tuman_col_w + i * prayer_col_w
            cx2 = cx1 + prayer_col_w
            cell_color = _lighten(col["color"], 0.12) if alt else col["color"]
            d.rectangle((cx1, ry1, cx2, ry2), fill=cell_color)
            t = row_data.get(col["key"]) or ""
            if t:
                d.text(
                    ((cx1 + cx2) // 2, (ry1 + ry2) // 2),
                    t, font=f_time, fill=COLOR_TIME_FG, anchor="mm",
                )
            elif not has_data:
                d.text(
                    ((cx1 + cx2) // 2, (ry1 + ry2) // 2),
                    "—", font=f_time, fill=(255, 255, 255, 120), anchor="mm",
                )

        if r < n_rows - 1:
            d.line((table_left, ry2, table_right, ry2), fill=COLOR_GRID, width=1*S)

    # ── MASJID ROW ────────────────────────────────────────────────────────
    msj_y1 = hdr_y2 + n_rows * DATA_ROW_H
    msj_y2 = msj_y1 + MASJID_ROW_H
    mosq   = _normalize_row(masjid_times or {})

    d.line((table_left, msj_y1, table_right, msj_y1), fill=COLOR_GRID, width=3*S)

    SUB1_H  = 48 * S
    sub1_y2 = msj_y1 + SUB1_H

    for idx, line in enumerate(("МАСЖИДЛАРДА", "ўқиладиган", "вақтлар")):
        d.text(
            (table_left + tuman_col_w // 2, msj_y1 + 26*S + idx * 32*S),
            line, font=f_masjid_h, fill=COLOR_MASJID_FG, anchor="mm",
        )

    for i, col in enumerate(PRAYER_COLUMNS):
        cx1 = table_left + tuman_col_w + i * prayer_col_w
        cx2 = cx1 + prayer_col_w
        cx_mid = (cx1 + cx2) // 2

        if col["key"] == "Quyosh":
            d.rectangle((cx1, msj_y1, cx2, msj_y2), fill=COLOR_FRAME)
            continue

        d.rectangle((cx1, msj_y1, cx2, sub1_y2), fill=COLOR_MASJID_HDR)
        d.text(
            (cx_mid, msj_y1 + SUB1_H // 2),
            col["cyr"], font=f_masjid_h, fill=COLOR_MASJID_FG, anchor="mm",
        )
        t = mosq.get(col["key"]) or EMPTY_MARK
        d.text(
            (cx_mid, sub1_y2 + (MASJID_ROW_H - SUB1_H) // 2),
            t, font=f_masjid_t, fill=COLOR_MASJID_FG, anchor="mm",
        )

    # ── DATE BANNER (gradient, rounded) ───────────────────────────────────
    DATE_H  = 86 * S
    date_y1 = table_bottom + 18 * S
    date_y2 = date_y1 + DATE_H

    _hgrad_rounded(img, (table_left, date_y1, table_right, date_y2),
                   COLOR_DATE_L, COLOR_DATE_R, radius=10*S)
    d = ImageDraw.Draw(img)

    cyr_month = CYR_MONTHS.get(target_date.month, str(target_date.month))
    d.text(
        (table_left + (table_right - table_left) // 2, date_y1 + DATE_H // 2),
        f"{target_date.day}-{cyr_month} {target_date.year} ЙИЛ УЧУН",
        font=f_date, fill=COLOR_DATE_FG, anchor="mm",
    )

    # ── FOOTER ────────────────────────────────────────────────────────────
    foot_y = date_y2 + 22 * S
    d.line((table_left, foot_y, table_right, foot_y), fill=COLOR_HDR_GOLD, width=2*S)
    foot_y += 14 * S

    for idx, line in enumerate((
        "Услуб: Ўзбекистон мусулмонлари идораси услуби бўйича",
        "кўрсатилган.",
    )):
        d.text(
            (table_left, foot_y + idx * 26*S),
            line, font=f_footer, fill=COLOR_FOOTER_FG, anchor="lm",
        )

    if test_mode:
        d.text(
            (table_right, foot_y + 26*S),
            "ТЕСТ РЕЖИМДА",
            font=f_test, fill=COLOR_TEST_FG, anchor="rm",
        )

    # ── Save — lossless PNG, compress_level=1 (fastest, largest, best) ────
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
