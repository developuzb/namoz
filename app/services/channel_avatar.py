"""Kanal avatarlarini (rasmlarini) avtomatik yasash va Telegram'ga o'rnatish servisi.

1000x1000 px premium dark-emerald + gold islomiy brending.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile
from PIL import Image, ImageDraw, ImageFont, ImageOps

from app.core.config import get_settings
from app.core.logger import logger
from app.db.models.channel import Channel
from app.services.backdrop import aqsa_backdrop

SIZE = (1000, 1000)
SS = 2  # Supersample 2x (2000x2000 render qilinib 1000x1000 ga LANCZOS bilan tushiriladi)

# Ranglar palitrasi (Qashqadaryo + TaqvimBot brendiga mos)
COLOR_BG_DARK = (10, 26, 20)        # to'q emerald charcoal
COLOR_BG_LIGHT = (18, 48, 36)       # yorqinroq emerald
COLOR_GLOW = (32, 90, 66)           # markazdagi yumshoq nur

COLOR_GOLD = (212, 175, 55)         # oltin rang
COLOR_GOLD_DARK = (160, 128, 36)    # to'qroq oltin
COLOR_WHITE = (255, 255, 255)       # sofdan oq
COLOR_TEXT_SUB = (200, 220, 210)    # och kumush-yashil matn


def _load_font(filename: str, size: int) -> ImageFont.FreeTypeFont:
    settings = get_settings()
    path = settings.static_dir / "fonts" / filename
    if path.exists():
        try:
            return ImageFont.truetype(str(path), size)
        except Exception as e:
            logger.warning("Font loading error {}: {}", path.name, e)
    for cand in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(cand, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _try_bold(font: ImageFont.FreeTypeFont, weight: int = 800) -> None:
    """Variable shriftni qalin qiladi — avval wght o'qi (ishonchli), keyin nom."""
    # 1) To'g'ridan-to'g'ri wght o'qi (Montserrat: 100–900)
    try:
        if hasattr(font, "set_variation_by_axes"):
            font.set_variation_by_axes([weight])
            return
    except (OSError, ValueError):
        pass
    # 2) Nomli variant (fallback)
    try:
        if hasattr(font, "get_variation_names") and hasattr(font, "set_variation_by_name"):
            names = font.get_variation_names()
            low = [n.lower() for n in names]
            for key in ("extrabold", "bold", "semibold"):
                if key in low:
                    font.set_variation_by_name(names[low.index(key)])
                    return
    except OSError:
        pass


def _glow(diam: int, color: tuple[int, int, int], max_alpha: int) -> Image.Image:
    """Yumshoq radial nur (markazda yorqin → chetда shaffof)."""
    grad = Image.radial_gradient("L").resize((diam, diam))
    alpha = ImageOps.invert(grad).point(lambda v: int((v / 255) * max_alpha))
    layer = Image.new("RGBA", (diam, diam), (*color, 0))
    layer.putalpha(alpha)
    return layer


def _fit_font(
    draw: ImageDraw.ImageDraw, text: str, path: str, start_px: int, max_w: int
) -> ImageFont.FreeTypeFont:
    """Matn `max_w` ga sig'guncha shrift o'lchamini kamaytiradi (qalin)."""
    size = start_px
    while size > 24:
        f = _load_font(path, size)
        _try_bold(f)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 6 * SS
    f = _load_font(path, size)
    _try_bold(f)
    return f


def generate_channel_avatar(title: str, subtitle: str = "NAMOZ VAQTLARI") -> Path:
    """Kanal nomi bo'yicha PROFESSIONAL profil rasmi (1000x1000 PNG).

    Chuqur emerald gradient + vinyetka, oltin bezakli halqa (rombli),
    nafis hilol + 8 qirrali yulduz (Rub-el-Hizb), pastda Masjidul Aqso
    silueti, qalin oltin sarlavha va oltin pill sub-title.
    """
    settings = get_settings()
    out_dir = settings.data_dir / "images" / "avatars"
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", title).strip("_") or "channel"
    out_path = out_dir / f"avatar_{safe_name}.png"

    w, h = SIZE[0] * SS, SIZE[1] * SS
    cx, cy = w // 2, h // 2

    # ── 1. Radial emerald fon + vinyetka (markaz yorqin → chet to'q) ──
    center_img = Image.new("RGB", (w, h), COLOR_BG_LIGHT)
    edge_img = Image.new("RGB", (w, h), (5, 15, 11))
    grad = Image.radial_gradient("L").resize((w, h))
    img = Image.composite(edge_img, center_img, grad).convert("RGBA")

    # ── 2. Emblema ortida issiq oltin-yashil nur ──
    g = _glow(int(w * 0.70), COLOR_GLOW, 80)
    img.alpha_composite(g, (cx - g.width // 2, int(h * 0.30) - g.height // 2))

    # ── 3. Pastda Masjidul Aqso silueti (skyline) ──
    m_w = int(w * 0.66)
    m_h = int(h * 0.20)
    mosque = aqsa_backdrop(width=m_w, height=m_h, color=COLOR_GOLD, alpha=60)
    img.alpha_composite(mosque, (cx - m_w // 2, int(h * 0.735)))

    draw = ImageDraw.Draw(img)

    # ── 4. Oltin bezakli ikki qavat halqa (doira ichida) + 4 romb ──
    ring_r = int(w * 0.445)
    draw.ellipse(
        [cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
        outline=COLOR_GOLD, width=5 * SS,
    )
    r2 = ring_r - 15 * SS
    draw.ellipse(
        [cx - r2, cy - r2, cx + r2, cy + r2],
        outline=COLOR_GOLD_DARK, width=2 * SS,
    )
    for ang in (90, 0, 270, 180):  # N, E, S, W
        dx = cx + int(ring_r * math.cos(math.radians(ang)))
        dy = cy - int(ring_r * math.sin(math.radians(ang)))
        ds = 13 * SS
        draw.polygon(
            [(dx, dy - ds), (dx + ds, dy), (dx, dy + ds), (dx - ds, dy)],
            fill=COLOR_GOLD,
        )

    # ── 5. Nafis hilol (maskali — fon gradientiga zarar bermaydi) ──
    R = 140 * SS
    mcx, mcy = cx, int(h * 0.315)
    cres = Image.new("L", (w, h), 0)
    cd = ImageDraw.Draw(cres)
    cd.ellipse([mcx - R, mcy - R, mcx + R, mcy + R], fill=255)
    ox = int(0.46 * R)
    cut = int(0.90 * R)
    cd.ellipse(
        [mcx - cut + ox, mcy - cut - int(0.06 * R),
         mcx + cut + ox, mcy + cut - int(0.06 * R)],
        fill=0,
    )
    gold_layer = Image.new("RGBA", (w, h), (*COLOR_GOLD, 0))
    gold_layer.putalpha(cres)
    img.alpha_composite(gold_layer)

    # ── 6. 8 qirrali yulduz (hilol ichida) ──
    sx, sy = mcx + int(0.66 * R), mcy
    sr = int(0.40 * R)
    star_pts = []
    for i in range(16):
        a = math.pi / 2 + i * math.pi / 8
        rad = sr if i % 2 == 0 else sr * 0.42
        star_pts.append((sx + rad * math.cos(a), sy - rad * math.sin(a)))
    ImageDraw.Draw(img).polygon(star_pts, fill=COLOR_GOLD)

    draw = ImageDraw.Draw(img)

    # ── 7. Sarlavha (QALIN, halqaga sig'adigan) ──
    title_path = "Montserrat-VariableFont_wght.ttf"
    clean = title.upper()
    max_w = int(2 * r2 * 0.80)
    tf = _fit_font(draw, clean, title_path, 128 * SS, max_w)
    ty = int(h * 0.55)
    # yumshoq soya + oltin-oq matn
    draw.text((cx + 3 * SS, ty + 3 * SS), clean, font=tf, fill=(0, 0, 0, 150), anchor="mm")
    draw.text((cx, ty), clean, font=tf, fill=(250, 246, 235), anchor="mm")

    # ── 8. Oltin ajratuvchi (romb + chiziqlar) ──
    dy2 = int(h * 0.635)
    dia = 9 * SS
    draw.line((cx - 130 * SS, dy2, cx - dia - 10 * SS, dy2), fill=COLOR_GOLD, width=3 * SS)
    draw.line((cx + dia + 10 * SS, dy2, cx + 130 * SS, dy2), fill=COLOR_GOLD, width=3 * SS)
    draw.polygon(
        [(cx, dy2 - dia), (cx + dia, dy2), (cx, dy2 + dia), (cx - dia, dy2)],
        fill=COLOR_GOLD,
    )

    # ── 9. Sub-title pill (oltin gradient, to'q qalin matn) ──
    sub_font = _load_font(title_path, 44 * SS)
    _try_bold(sub_font)
    sub_text = subtitle.upper()
    sw = draw.textlength(sub_text, font=sub_font)
    pill_w = int(sw + 84 * SS)
    pill_h = int(72 * SS)
    px = cx - pill_w // 2
    py = int(h * 0.685)
    # oltin gradient pill
    band = Image.new("RGB", (pill_w, 1))
    for i in range(pill_w):
        t = i / max(pill_w - 1, 1)
        band.putpixel((i, 0), (
            int(COLOR_GOLD[0] + (COLOR_GOLD_DARK[0] - COLOR_GOLD[0]) * t),
            int(COLOR_GOLD[1] + (COLOR_GOLD_DARK[1] - COLOR_GOLD[1]) * t),
            int(COLOR_GOLD[2] + (COLOR_GOLD_DARK[2] - COLOR_GOLD[2]) * t),
        ))
    pill = band.resize((pill_w, pill_h)).convert("RGBA")
    mask = Image.new("L", (pill_w, pill_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, pill_w, pill_h), radius=pill_h // 2, fill=255,
    )
    pill.putalpha(mask)
    img.alpha_composite(pill, (px, py))
    ImageDraw.Draw(img).text(
        (cx, py + pill_h // 2), sub_text, font=sub_font,
        fill=(20, 40, 28), anchor="mm",
    )

    # ── 10. Yakuniy: 1000x1000 ga LANCZOS + PNG ──
    final_img = img.convert("RGB").resize(SIZE, Image.Resampling.LANCZOS)
    final_img.save(out_path, "PNG", optimize=True)
    logger.info("Kanal avatari yaratildi: {}", out_path)
    return out_path


async def update_channel_avatar(bot: Bot, channel: Channel) -> tuple[bool, str]:
    """Bitta kanal uchun rasm yaratadi va Telegram'ga avatar qilib qo'yadi."""
    title = channel.title or (channel.region.name if channel.region else "nmsupportbot")
    try:
        avatar_path = generate_channel_avatar(title=title)
        photo = FSInputFile(str(avatar_path))
        await bot.set_chat_photo(chat_id=channel.chat_id, photo=photo)
        logger.info("Kanal rasm muvaffaqiyatli qo'yildi: chat_id={} ({})", channel.chat_id, title)
        return True, "OK"
    except Exception as e:
        err_msg = str(e)
        logger.error("Kanal rasmini qo'yishda xatolik (chat_id={}): {}", channel.chat_id, err_msg)
        return False, err_msg
