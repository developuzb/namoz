"""Qibla yo'nalishini hisoblash va kompas rasmini yasash.

Qibla — har joydan Ka'bagacha yo'nalish (azimuth, true north'dan soat strelkasi
bo'yicha gradus). Geodesik formulada hisoblanadi (great circle bearing).
"""
from __future__ import annotations

import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.core.config import get_settings
from app.core.logger import logger

#: Ka'ba (Makkah, Saudiya) koordinatalari — Masjid al-Haram
KAABA_LAT = 21.4225
KAABA_LON = 39.8262


def calculate_qibla_bearing(lat: float, lon: float) -> float:
    """
    Qibla azimuthi (true north'dan soat strelkasi bo'yicha 0–360°).

    Formula: spherical great-circle initial bearing.
    """
    phi1 = math.radians(lat)
    phi2 = math.radians(KAABA_LAT)
    delta_lambda = math.radians(KAABA_LON - lon)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = (
        math.cos(phi1) * math.sin(phi2)
        - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    )
    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360) % 360  # 0..360


def calculate_qibla_distance_km(lat: float, lon: float) -> float:
    """Ka'bagacha bo'lgan yer yuzi masofasi (Haversine, km)."""
    r = 6371.0
    phi1 = math.radians(lat)
    phi2 = math.radians(KAABA_LAT)
    dphi = math.radians(KAABA_LAT - lat)
    dlambda = math.radians(KAABA_LON - lon)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def _bearing_label(bearing: float) -> str:
    """Azimuthni 8-yo'nalishli label'ga (N, NE, ...) aylantirish."""
    dirs = [
        ("Sh", 0), ("ShShO'", 22.5), ("ShO'", 45), ("OShShO'", 67.5),
        ("O'", 90), ("OJShO'", 112.5), ("JShO'", 135), ("JJShO'", 157.5),
        ("J", 180), ("JJG'", 202.5), ("JG'", 225), ("OJG'", 247.5),
        ("G'", 270), ("OShG'", 292.5), ("ShG'", 315), ("ShShG'", 337.5),
    ]
    # Eng yaqin label
    best = min(dirs, key=lambda x: min(abs(x[1] - bearing), 360 - abs(x[1] - bearing)))
    return best[0]


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    return cleaned or "qibla"


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


def _load_font(filename: str, size: int) -> ImageFont.FreeTypeFont:
    settings = get_settings()
    path = settings.static_dir / "fonts" / filename
    if path.exists():
        try:
            return ImageFont.truetype(str(path), size)
        except OSError:
            pass
    return ImageFont.load_default()  # type: ignore[return-value]


def make_qibla_image(
    *,
    region_name: str,
    latitude: float,
    longitude: float,
    out_filename: str | None = None,
    size: int = 900,
) -> tuple[Path, float, float]:
    """
    Qibla kompas rasmini yasaydi.

    Returns:
        (path, bearing_degrees, distance_km)
    """
    settings = get_settings()
    bearing = calculate_qibla_bearing(latitude, longitude)
    distance = calculate_qibla_distance_km(latitude, longitude)

    W = H = size

    # ============== Fon (cream gradient) ==============
    img = Image.new("RGBA", (W, H), (252, 245, 230, 255))
    d = ImageDraw.Draw(img)

    cx, cy = W // 2, H // 2 + 40

    # ============== Doira (kompas) ==============
    radius = int(W * 0.36)
    # Soya
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse(
        (cx - radius - 8, cy - radius + 4, cx + radius + 8, cy + radius + 16),
        fill=(0, 0, 0, 80),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    img.alpha_composite(shadow)

    # Doira tashqi halqa (oltin)
    d.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        fill=(255, 252, 240),
        outline=(212, 165, 95),
        width=6,
    )
    # Doira ichki halqa
    inner_r = radius - 18
    d.ellipse(
        (cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r),
        fill=(255, 255, 255),
        outline=(220, 200, 160),
        width=2,
    )

    # ============== Yo'nalishlar (N/E/S/W) ==============
    f_dir = _load_font("Montserrat-VariableFont_wght.ttf", 48)
    cardinals = [
        ("Sh", 0),    # Shimol (North)
        ("O'", 90),   # O'ng = East
        ("J", 180),   # Janub (South)
        ("G'", 270),  # G'arb (West)
    ]
    for label, angle in cardinals:
        # angle 0 = up (N), clockwise
        rad = math.radians(angle - 90)  # -90 to put 0 at top
        lx = cx + int((inner_r - 50) * math.cos(rad))
        ly = cy + int((inner_r - 50) * math.sin(rad))
        d.text((lx, ly), label, font=f_dir, fill=(60, 50, 80), anchor="mm")

    # Mayda chiziqchalar (har 30°)
    for deg in range(0, 360, 30):
        rad = math.radians(deg - 90)
        x1 = cx + int(inner_r * math.cos(rad))
        y1 = cy + int(inner_r * math.sin(rad))
        x2 = cx + int((inner_r - 14) * math.cos(rad))
        y2 = cy + int((inner_r - 14) * math.sin(rad))
        d.line((x1, y1, x2, y2), fill=(180, 150, 110), width=2)

    # ============== Qibla strelka ==============
    arrow_rad = math.radians(bearing - 90)
    arrow_len = int(inner_r * 0.78)
    ax = cx + int(arrow_len * math.cos(arrow_rad))
    ay = cy + int(arrow_len * math.sin(arrow_rad))

    # Strelka tanasi (qalin chiziq)
    d.line((cx, cy, ax, ay), fill=(212, 80, 60), width=10)
    # Uchburchak boshi
    head_size = 32
    h_rad1 = arrow_rad + math.radians(150)
    h_rad2 = arrow_rad - math.radians(150)
    hx1 = ax + int(head_size * math.cos(h_rad1))
    hy1 = ay + int(head_size * math.sin(h_rad1))
    hx2 = ax + int(head_size * math.cos(h_rad2))
    hy2 = ay + int(head_size * math.sin(h_rad2))
    d.polygon([(ax, ay), (hx1, hy1), (hx2, hy2)], fill=(212, 80, 60))

    # Markaz nuqtasi
    d.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), fill=(60, 50, 80))
    d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=(255, 255, 255))

    # Ka'ba emoji strelka uchida
    kaaba = _load_emoji("kaaba.png", 80)
    if kaaba:
        # Strelka uchidan biroz nariga
        ka_rad = arrow_rad
        kx = cx + int((arrow_len + 50) * math.cos(ka_rad))
        ky = cy + int((arrow_len + 50) * math.sin(ka_rad))
        img.alpha_composite(kaaba, (kx - 40, ky - 40))

    # ============== Header ==============
    f_title = _load_font("Montserrat-VariableFont_wght.ttf", 56)
    d.text(
        (W // 2, 70), "QIBLA YO'NALISHI",
        font=f_title, fill=(50, 30, 70), anchor="mm",
    )
    f_sub = _load_font("Inter-VariableFont_opsz,wght.ttf", 32)
    d.text(
        (W // 2, 130), region_name,
        font=f_sub, fill=(100, 90, 110), anchor="mm",
    )

    # ============== Footer (info) ==============
    f_info = _load_font("Manrope-VariableFont_wght.ttf", 38)
    d.text(
        (W // 2, H - 130),
        f"Azimut: {bearing:.1f}°  ({_bearing_label(bearing)})",
        font=f_info, fill=(50, 30, 70), anchor="mm",
    )
    d.text(
        (W // 2, H - 75),
        f"Ka'bagacha: {distance:,.0f} km",
        font=f_info, fill=(100, 90, 110), anchor="mm",
    )

    # ============== Saqlash ==============
    if out_filename:
        out_path = settings.images_dir / out_filename
    else:
        out_path = settings.images_dir / f"qibla_{_safe_filename(region_name)}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out_path, optimize=True, quality=92)
    logger.debug("Qibla rasm saqlandi: {}", out_path)

    return out_path, bearing, distance


__all__ = [
    "calculate_qibla_bearing",
    "calculate_qibla_distance_km",
    "make_qibla_image",
]
