"""Orqa fon dekorlari — Masjidul Aqso (Qubbat as-Saxra) sileti.

`aqsa_backdrop()` berilgan o'lchamda xira, bir rangli silet-band qaytaradi.
Agar `static/backdrops/aqsa.png` mavjud bo'lsa, chizilgan silet o'rniga
o'sha rasm (alpha kanalidan mask sifatida) ishlatiladi — dizaynerlar
keyinchalik sifatliroq rasm qo'yishi mumkin.
"""
from __future__ import annotations

from PIL import Image, ImageDraw

from app.core.config import get_settings
from app.core.logger import logger

_OVERRIDE_FILENAME = "aqsa.png"

#: Bir martalik yuklab olish manzili — fayl diskda bo'lmasa shu yerdan
#: olinadi va keshga saqlanadi. Keyin tarmoq kerak bo'lmaydi.
_DEFAULT_URL = (
    "https://d8j0ntlcm91z4.cloudfront.net/user_3EheebtkxrfUUdMPzZvLc5v0chP/"
    "hf_20260703_182318_47223ad2-7ae0-4396-a83c-a15a9b766dc2.png"
)

#: Yuklab olish muvaffaqiyatsiz bo'lsa qayta urinmaslik uchun flag
_download_failed = False


def aqsa_backdrop(
    *,
    width: int,
    height: int,
    color: tuple[int, int, int] = (214, 176, 98),
    alpha: int = 26,
) -> Image.Image:
    """Xira Masjidul Aqso sileti (RGBA layer, shaffof fon).

    Args:
        width/height: band o'lchami (px)
        color: silet rangi (odatda oltin)
        alpha: maksimal xiralik (0-255, past = xiraroq)
    """
    mask = _load_override_mask(width, height)
    if mask is None:
        mask = _draw_silhouette_mask(width, height)

    def _level(v: int) -> int:
        if v < 24:      # qora fon / shovqin
            return 0
        if v >= 128:    # to'liq shakl
            return alpha
        return int(alpha * v / 128)  # chetlardagi antialiasing

    layer = Image.new("RGBA", (width, height), (*color, 0))
    layer.putalpha(mask.point(_level))
    return layer


def _ensure_asset(path) -> bool:
    """Fayl yo'q bo'lsa — bir marta yuklab olishga urinadi. Returns: mavjudmi."""
    global _download_failed
    if path.exists():
        return True
    if _download_failed:
        return False
    try:
        import httpx

        path.parent.mkdir(parents=True, exist_ok=True)
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            resp = client.get(_DEFAULT_URL)
            resp.raise_for_status()
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(resp.content)
        tmp.replace(path)
        logger.info("Aqsa backdrop yuklab olindi: {} ({} bayt)", path, len(resp.content))
        return True
    except Exception as e:  # noqa: BLE001 — tarmoq xatosi renderni to'xtatmasin
        _download_failed = True
        logger.warning("Aqsa backdrop yuklab olinmadi ({}), chizilgan silet ishlatiladi", e)
        return False


def _load_override_mask(width: int, height: int) -> Image.Image | None:
    """static/backdrops/aqsa.png bo'lsa — undan mask yasaydi."""
    path = get_settings().static_dir / "backdrops" / _OVERRIDE_FILENAME
    if not _ensure_asset(path):
        return None
    try:
        src = Image.open(path).convert("RGBA")
    except (OSError, ValueError) as e:
        logger.warning("Aqsa backdrop rasmi yuklanmadi {}: {}", path, e)
        return None

    # Balandlikka moslab, markazga joylash (eniga sig'masa — kesmasdan toraytirish)
    ratio = height / src.size[1]
    new_w = max(1, int(src.size[0] * ratio))
    new_h = height
    if new_w > width:
        new_h = max(1, int(height * width / new_w))
        new_w = width
    src = src.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Mask: alpha kanali ma'noli bo'lsa — undan; aks holda (qora fonli
    # rasm) yorqinlikdan. AI-generatsiya rasmlarda odatda alpha yo'q.
    a = src.getchannel("A")
    lo, hi = a.getextrema()
    part = a if hi - lo > 16 else src.convert("L")

    mask = Image.new("L", (width, height), 0)
    mask.paste(part, (width // 2 - new_w // 2, height - new_h))
    return mask


def _draw_silhouette_mask(w: int, h: int) -> Image.Image:
    """Stilizatsiyalangan Aqso majmuasi: devor, Qubbat as-Saxra, minoralar."""
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    F = 255  # to'ldirish

    # ── Devor (pastki tayanch) + tishlar (crenellation) ───────────────────
    wall_h = int(0.10 * h)
    wall_top = h - wall_h
    d.rectangle((0, wall_top, w, h), fill=F)

    merlon_h = max(2, int(0.05 * h))
    step = max(4, int(0.055 * h))
    x = 0
    while x < w:
        d.rectangle((x, wall_top - merlon_h, x + step, wall_top), fill=F)
        x += step * 2

    cx = w // 2

    # ── Yon binolar: kichik gumbazli qanotlar (al-Qibli uslubida) ─────────
    for sx in (int(0.36 * w), int(0.64 * w)):
        bw = int(0.22 * h)   # bino yarim kengligi
        bh = int(0.10 * h)   # bino balandligi
        dr = int(0.15 * h)   # gumbaz radiusi
        b_top = wall_top - bh
        d.rectangle((sx - bw, b_top, sx + bw, wall_top), fill=F)
        d.pieslice((sx - dr, b_top - dr, sx + dr, b_top + dr), 180, 360, fill=F)

    # ── Markaz: Qubbat as-Saxra ───────────────────────────────────────────
    base_hw_bot = int(0.58 * h)
    base_hw_top = int(0.46 * h)
    base_h = int(0.24 * h)
    base_top = wall_top - base_h
    d.polygon(
        [
            (cx - base_hw_bot, wall_top),
            (cx - base_hw_top, base_top),
            (cx + base_hw_top, base_top),
            (cx + base_hw_bot, wall_top),
        ],
        fill=F,
    )
    # Karniz
    cor_hw = int(0.54 * h)
    d.rectangle((cx - cor_hw, base_top - int(0.030 * h), cx + cor_hw, base_top), fill=F)

    # Baraban (drum)
    drum_hw = int(0.30 * h)
    drum_h = int(0.11 * h)
    drum_top = base_top - int(0.030 * h) - drum_h
    d.rectangle((cx - drum_hw, drum_top, cx + drum_hw, base_top), fill=F)

    # Gumbaz — yarim ellips
    dome_hw = int(0.36 * h)
    dome_h = int(0.32 * h)
    dome_top = drum_top - dome_h
    d.pieslice(
        (cx - dome_hw, dome_top, cx + dome_hw, dome_top + 2 * dome_h),
        180, 360, fill=F,
    )

    # Uchlik: tayoqcha + hilol
    rod_hw = max(1, int(0.010 * h))
    rod_top = dome_top - int(0.08 * h)
    d.rectangle((cx - rod_hw, rod_top, cx + rod_hw, dome_top + 2), fill=F)

    cr = int(0.055 * h)
    cy = rod_top - cr
    d.ellipse((cx - cr, cy - cr, cx + cr, cy + cr), fill=F)
    # Hilol kesigi
    off = int(cr * 0.55)
    er = int(cr * 0.85)
    d.ellipse((cx - er + off, cy - er - off // 2, cx + er + off, cy + er - off // 2), fill=0)

    # ── Minoralar (chap/o'ng) ─────────────────────────────────────────────
    for mx in (int(0.22 * w), int(0.78 * w)):
        shaft_hw = int(0.035 * h)
        shaft_top = wall_top - int(0.50 * h)
        d.rectangle((mx - shaft_hw, shaft_top, mx + shaft_hw, wall_top), fill=F)
        # Balkon (sharafa)
        bal_hw = int(0.062 * h)
        bal_h = int(0.035 * h)
        d.rectangle((mx - bal_hw, shaft_top - bal_h, mx + bal_hw, shaft_top), fill=F)
        # Yuqori qism
        up_hw = int(0.024 * h)
        up_top = shaft_top - bal_h - int(0.11 * h)
        d.rectangle((mx - up_hw, up_top, mx + up_hw, shaft_top - bal_h), fill=F)
        # Konus uchi
        cone_hw = int(0.048 * h)
        cone_top = up_top - int(0.11 * h)
        d.polygon(
            [(mx - cone_hw, up_top), (mx, cone_top), (mx + cone_hw, up_top)],
            fill=F,
        )
        # Uch nuqtasi
        tr = max(1, int(0.014 * h))
        d.ellipse((mx - tr, cone_top - 2 * tr - 2, mx + tr, cone_top - 2), fill=F)

    return mask


__all__ = ["aqsa_backdrop"]
