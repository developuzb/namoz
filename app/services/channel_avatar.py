"""Kanal avatarlarini (rasmlarini) avtomatik yasash va Telegram'ga o'rnatish servisi.

1000x1000 px premium dark-emerald + gold islomiy brending.
"""
from __future__ import annotations

import re
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.core.config import get_settings
from app.core.logger import logger
from app.db.models.channel import Channel

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


def generate_channel_avatar(title: str, subtitle: str = "NAMOZ VAQTLARI") -> Path:
    """Kanal nomi bo'yicha profil rasmi (1000x1000 PNG) yasaydi."""
    settings = get_settings()
    out_dir = settings.data_dir / "images" / "avatars"
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", title).strip("_") or "channel"
    out_path = out_dir / f"avatar_{safe_name}.png"

    # Supersampled canvas (2000x2000)
    w, h = SIZE[0] * SS, SIZE[1] * SS
    img = Image.new("RGBA", (w, h), COLOR_BG_DARK)

    # 1. Radial Background Gradient
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    cx, cy = w // 2, h // 2
    max_r = int(w * 0.65)
    for r in range(max_r, 0, -20):
        alpha = int(90 * (1 - r / max_r) ** 1.5)
        glow_draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(COLOR_GLOW[0], COLOR_GLOW[1], COLOR_GLOW[2], alpha),
        )
    glow = glow.filter(ImageFilter.GaussianBlur(40 * SS))
    img = Image.alpha_composite(img, glow)

    draw = ImageDraw.Draw(img)

    # 2. Outer Decorative Gold Border (Halqa ramka)
    margin = 50 * SS
    ring_r = (w // 2) - margin
    # Oltin halqa (Tashqi va ichki nozik halqalar)
    draw.ellipse(
        [cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
        outline=COLOR_GOLD,
        width=6 * SS,
    )
    inner_ring_r = ring_r - (16 * SS)
    draw.ellipse(
        [cx - inner_ring_r, cy - inner_ring_r, cx + inner_ring_r, cy + inner_ring_r],
        outline=COLOR_GOLD_DARK,
        width=2 * SS,
    )

    # 3. Top Emblem (Hilol / Masjid belgisi)
    # Hilol (Crescent Moon) chizish
    moon_cx, moon_cy = cx, cy - (180 * SS)
    moon_r = 90 * SS
    # Oltin doira
    draw.ellipse(
        [moon_cx - moon_r, moon_cy - moon_r, moon_cx + moon_r, moon_cy + moon_r],
        fill=COLOR_GOLD,
    )
    # To'q kesuvchi doira (Hilol shaklini hosil qilish)
    offset_x = 30 * SS
    draw.ellipse(
        [moon_cx - moon_r + offset_x, moon_cy - moon_r - (5 * SS),
         moon_cx + moon_r + offset_x, moon_cy + moon_r - (5 * SS)],
        fill=COLOR_BG_DARK,
    )

    # Hilol ustidagi kichik 8 qirrali yulduz / nuqta
    star_x, star_y = moon_cx - (20 * SS), moon_cy - (10 * SS)
    draw.ellipse(
        [star_x - (10 * SS), star_y - (10 * SS), star_x + (10 * SS), star_y + (10 * SS)],
        fill=COLOR_GOLD,
    )

    # 4. Title Text (Kanal yoki Hudud nomi)
    title_font = _load_font("Montserrat-VariableFont_wght.ttf", 85 * SS)
    sub_font = _load_font("Inter-VariableFont_opsz,wght.ttf", 45 * SS)

    # Sarlavhani tozalash va tayyorlash
    clean_title = title.upper()

    # Agar matn judayam uzun bo'lsa, 2 qatorga bo'lamiz
    words = clean_title.split()
    if len(words) > 2:
        mid = len(words) // 2
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:])
        lines = [line1, line2]
    else:
        lines = [clean_title]

    # Matnlarni chizish
    curr_y = cy + (40 * SS)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        lx = (w - lw) // 2
        # Soya va oq matn
        draw.text((lx + (3 * SS), curr_y + (3 * SS)), line, font=title_font, fill=(0, 0, 0, 160))
        draw.text((lx, curr_y), line, font=title_font, fill=COLOR_WHITE)
        curr_y += lh + (25 * SS)

    # 5. Subtitle Pill Badge ("NAMOZ VAQTLARI")
    sub_text = subtitle.upper()
    s_bbox = draw.textbbox((0, 0), sub_text, font=sub_font)
    sw = s_bbox[2] - s_bbox[0]
    sh = s_bbox[3] - s_bbox[1]

    pill_w = sw + (80 * SS)
    pill_h = sh + (40 * SS)
    pill_x = (w - pill_w) // 2
    pill_y = curr_y + (40 * SS)

    # Gold Pill background
    draw.rounded_rectangle(
        [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
        radius=pill_h // 2,
        fill=COLOR_GOLD,
    )
    # Subtitle Text inside Pill (Dark text for high contrast)
    st_x = (w - sw) // 2
    st_y = pill_y + (s_bbox[1] if s_bbox[1] < 0 else 0) + ((pill_h - sh) // 2) - (2 * SS)
    draw.text((st_x, st_y), sub_text, font=sub_font, fill=COLOR_BG_DARK)

    # Downsample to final SIZE (1000x1000)
    final_img = img.resize(SIZE, Image.Resampling.LANCZOS)
    final_img.save(out_path, "PNG", quality=95)
    logger.info("Kanal avatari yaratildi: {}", out_path)
    return out_path


async def update_channel_avatar(bot: Bot, channel: Channel) -> tuple[bool, str]:
    """Bitta kanal uchun rasm yaratadi va Telegram'ga avatar qilib qo'yadi."""
    title = channel.title or (channel.region.name if channel.region else "TaqvimBot")
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
