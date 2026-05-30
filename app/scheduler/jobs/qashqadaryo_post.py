"""Qashqadaryo plakatini har kuni belgilangan chat ga yuboradi.

Pipeline:
  1) `Qashqadaryo viloyati` ning 14 tumanini DB dan oladi
  2) Har biri uchun bugungi vaqtlarni PrayerService chain orqali oladi
  3) Plakat PNG ni `render_qashqadaryo_table` bilan yasaydi
  4) `NAMOZ_CHAT_ID` ga rasm yuboradi va `post_logs` ga yozadi

Ham scheduler ham `/test_namoz` handler tomonidan chaqiriladi.
"""
from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.types import FSInputFile

from app.core.config import get_settings
from app.core.constants import FARZ_PRAYERS
from app.core.exceptions import ProviderError
from app.core.logger import logger
from app.db.repositories.masjid_time_repo import MasjidTimeRepository
from app.db.repositories.post_log_repo import PostLogRepository
from app.db.repositories.region_repo import RegionRepository
from app.db.session import get_session
from app.services.qashqadaryo_table import (
    TUMAN_ORDER_CYR,
    render_qashqadaryo_table,
)
from app.services.registry import get_prayer_service

#: Viloyat (parent) slug — seed migratsiyasidan
PARENT_SLUG = "qashqadaryo"


async def build_qashqadaryo_image(
    *, target_date: date | None = None, test_mode: bool = False,
) -> tuple[Path, dict[str, dict[str, str]], dict[str, str]]:
    """14 tuman uchun vaqtlarni topib, plakat rasmni yasaydi.

    Returns:
        (rasm yo'li, tuman_lotin_nomi -> times dict, masjid vaqtlari dict)

    Raises:
        ValueError — Qashqadaryo viloyati DB da topilmasa.
        ProviderError — bironta tuman uchun ham vaqt topilmasa.
    """
    target_date = target_date or date.today()

    async with get_session() as session:
        rr = RegionRepository(session)
        mt_repo = MasjidTimeRepository(session)

        parent = await rr.get_by_slug(PARENT_SLUG)
        if parent is None:
            raise ValueError(
                f"Qashqadaryo viloyati DB da topilmadi (slug={PARENT_SLUG})"
            )

        tumans = await rr.list_children(parent.id)
        if not tumans:
            raise ValueError("Qashqadaryo tumanlari topilmadi")

        # DB nomlarini normallashtirish: tipografik apostrof (U+2018/2019/02BB)
        # → oddiy ASCII apostrof (U+0027) — TUMAN_ORDER_CYR bilan moslashtirish uchun
        def _norm(s: str) -> str:
            return s.replace("‘", "'").replace("’", "'").replace("ʻ", "'")

        tuman_by_name = {_norm(t.name): t for t in tumans}
        prayer_service = get_prayer_service()

        regions_data: dict[str, dict[str, str]] = {}
        success = 0
        for lotin, _cyr in TUMAN_ORDER_CYR:
            region = tuman_by_name.get(lotin)
            if region is None:
                logger.warning("Tuman DB da topilmadi: {}", lotin)
                continue
            try:
                times = await prayer_service.fetch_for_region(region, target_date)
                regions_data[lotin] = times.times
                success += 1
            except ProviderError as e:
                logger.error(
                    "Qashqadaryo post: {} uchun vaqt olinmadi: {}", lotin, e,
                )

        if success == 0:
            raise ProviderError(
                "Qashqadaryo: 14 tuman ichidan birortasi ham olinmadi"
            )

        # Jamoat vaqtlari — viloyat parent uchun yagona to'plam.
        # 14 tumanga bir xil — admin shu yerdan bir joydan tahrirlaydi.
        m = await mt_repo.get_for_region(parent.id)
        masjid = {p: m.get(p, "") for p in FARZ_PRAYERS if m.get(p)}

        logger.info(
            "🗂 Qashqadaryo plakat: {}/{} tuman vaqtlari olindi, masjid={} ta",
            success, len(TUMAN_ORDER_CYR), len(masjid),
        )

    image_path = render_qashqadaryo_table(
        target_date=target_date,
        regions_data=regions_data,
        masjid_times=masjid or None,
        test_mode=test_mode,
    )
    return image_path, regions_data, masjid


_MASJID_CYR: dict[str, str] = {
    "Bomdod": "Бомдод",
    "Peshin": "Пешин",
    "Asr":    "Аср",
    "Shom":   "Шом",
    "Xufton": "Хуфтон",
}

_MASJID_EMOJI: dict[str, str] = {
    "Bomdod": "🌙",
    "Peshin": "☀️",
    "Asr":    "⛅",
    "Shom":   "🌅",
    "Xufton": "🌑",
}


def _calc_tahajjud(
    regions_data: dict[str, dict[str, str]] | None,
    target_date: date,
) -> str | None:
    """14 tumanga umumiy Tahajjud oraligi (Qarshi — viloyat markazi asosida).

    Tahajjud kechaning oxirgi 1/3 qismi (Xuftondan ertangi Bomdodgacha).
    Returns: "HH:MM — HH:MM" yoki None.
    """
    if not regions_data:
        return None
    import pytz

    from app.core.config import get_settings
    from app.services.time_calculator import calculate_nafl_windows

    # Qarshi — viloyat markazi; agar yo'q bo'lsa, birinchi mavjud tumandan
    base = regions_data.get("Qarshi") or next(iter(regions_data.values()), None)
    if not base:
        return None

    tz = pytz.timezone(get_settings().TIMEZONE)
    windows = calculate_nafl_windows(
        region_times=base,
        masjid_times={},
        target_date=target_date,
        tz=tz,
    )
    return windows.get("Tahajjud")


def _calc_sahar_iftor(
    masjid_times: dict[str, str] | None,
    regions_data: dict[str, dict[str, str]] | None,
) -> tuple[str, str]:
    """Umumiy saharlik (Bomdod) va iftorlik (Shom) qaytaradi."""
    if masjid_times:
        s = masjid_times.get("Bomdod", "")
        i = masjid_times.get("Shom", "")
        if s and i:
            return s, i

    if regions_data:
        def _avg(key: str) -> str:
            vals = [v[key] for v in regions_data.values() if v.get(key)]
            if not vals:
                return ""
            total = 0
            for t in vals:
                try:
                    total += int(t[:2]) * 60 + int(t[3:5])
                except (ValueError, IndexError):
                    pass
            avg = total // len(vals)
            return f"{avg // 60:02d}:{avg % 60:02d}"
        return _avg("Bomdod"), _avg("Shom")

    return "", ""


def default_caption(
    target_date: date,
    masjid_times: dict[str, str] | None = None,
    regions_data: dict[str, dict[str, str]] | None = None,
) -> str:
    """Kanalga yuboriladigan standart caption."""
    from app.services.hijri_service import gregorian_to_hijri_uz
    from app.services.qashqadaryo_table import TUMAN_ORDER_CYR
    from app.utils.text_utils import format_milodiy_uz, weekday_uz
    from datetime import datetime as _dt

    dt = _dt(target_date.year, target_date.month, target_date.day)
    milodiy = format_milodiy_uz(dt)
    hafta = weekday_uz(dt)
    try:
        hijriy = gregorian_to_hijri_uz(target_date)
    except Exception:  # noqa: BLE001
        hijriy = ""

    lines = [
        "📍 <b>Қашқадарё вилояти намоз вақтлари</b>",
        f"🗓 <b>{milodiy} ({hafta})</b>",
    ]
    if hijriy:
        lines.append(f"🕌 <i>{hijriy}</i>")

    # ── Masjid vaqtlari — blockquote ──────────────────────────────────────
    if masjid_times:
        msj = ["🕌 <b>Масжидларда ўқиладиган вақтлар:</b>"]
        for key, cyr in _MASJID_CYR.items():
            t = masjid_times.get(key)
            if t:
                em = _MASJID_EMOJI.get(key, "•")
                msj.append(f"{em} {cyr}: <b>{t}</b>")
        lines.append("")
        lines.append("<blockquote>" + "\n".join(msj) + "</blockquote>")

    # ── Umumiy saharlik va iftorlik ───────────────────────────────────────
    sahar, iftor = _calc_sahar_iftor(masjid_times, regions_data)
    if sahar or iftor:
        lines.append("")
        if sahar:
            lines.append(f"🌙 <b>Саҳарлик:</b> <code>{sahar}</code>")
        if iftor:
            lines.append(f"🌇 <b>Ифторлик:</b> <code>{iftor}</code>")

    # ── Tahajjud oraligi (barcha tumanlarga umumiy) ───────────────────────
    tahajjud = _calc_tahajjud(regions_data, target_date)
    if tahajjud:
        lines.append(f"🌃 <b>Таҳажжуд:</b> <code>{tahajjud}</code>")

    # ── 14 tuman saharlik / iftorlik ──────────────────────────────────────
    if regions_data:
        rows = ["🏙 <b>Туманлар (🌙саҳар / 🌅ифтор):</b>"]
        for lotin, cyr in TUMAN_ORDER_CYR:
            row = regions_data.get(lotin, {})
            s = row.get("Bomdod") or "—"
            i = row.get("Shom") or "—"
            rows.append(f"• {cyr}: <b>{s}</b> / <b>{i}</b>")
        lines.append("")
        lines.append("<blockquote>" + "\n".join(rows) + "</blockquote>")

    lines.append("")
    lines.append("📲 <a href=\"https://t.me/+5hl-bKo-Ec5hOGNi\">Kanalga obuna bo'ling</a>")

    return "\n".join(lines)


async def publish_existing_image(
    bot: Bot,
    *,
    chat_id: int,
    image_path: str,
    caption: str | None = None,
    target_date: date | None = None,
    masjid_times: dict[str, str] | None = None,
    regions_data: dict[str, dict[str, str]] | None = None,
) -> bool:
    """Allaqachon yasalgan rasmni `chat_id` ga yuboradi. Re-render qilmaydi."""
    target_date = target_date or date.today()
    return await _send_photo_safe(
        bot=bot,
        chat_id=chat_id,
        image_path=image_path,
        caption=caption or default_caption(target_date, masjid_times, regions_data),
        post_type="qashqadaryo",
    )


async def send_qashqadaryo_post(
    bot: Bot,
    *,
    chat_id: int,
    target_date: date | None = None,
    test_mode: bool = False,
) -> bool:
    """Plakatni yasab `chat_id` ga yuboradi. ``True`` — muvaffaqiyatli.

    Telegram xatolarini log qiladi va `post_logs` ga yozadi.
    """
    target_date = target_date or date.today()

    try:
        image_path, regions_data, masjid = await build_qashqadaryo_image(
            target_date=target_date, test_mode=test_mode,
        )
    except (ValueError, ProviderError) as e:
        logger.error("Qashqadaryo plakat yasalmadi: {}", e)
        async with get_session() as session:
            await PostLogRepository(session).log(
                region_id=None, chat_id=chat_id,
                post_type="qashqadaryo", status="error", error=str(e),
            )
        return False

    caption = default_caption(target_date, masjid or None, regions_data or None)
    if test_mode:
        caption = "🧪 <b>ТЕСТ режим</b>\n\n" + caption

    return await _send_photo_safe(
        bot=bot,
        chat_id=chat_id,
        image_path=str(image_path),
        caption=caption,
        post_type="qashqadaryo",
    )


async def run_qashqadaryo_post(bot: Bot) -> None:
    """Scheduler chaqiradigan entry point — `NAMOZ_CHAT_ID` ga yuboradi."""
    settings = get_settings()
    chat_id = settings.namoz_chat_id
    if not chat_id:
        logger.warning(
            "NAMOZ_CHAT_ID o'rnatilmagan — Qashqadaryo plakat yuborilmaydi"
        )
        return

    ok = await send_qashqadaryo_post(bot, chat_id=chat_id)
    logger.info("Qashqadaryo kunlik post: {}", "OK" if ok else "FAIL")


async def _send_photo_safe(
    *,
    bot: Bot,
    chat_id: int,
    image_path: str,
    caption: str,
    post_type: str,
) -> bool:
    """Photo + HD document ketma-ket yuboradi, xatolarni post_logs ga yozadi."""
    from pathlib import Path as _Path
    filename = _Path(image_path).name

    async with get_session() as session:
        log_repo = PostLogRepository(session)

        for attempt in range(2):
            try:
                # 1) Siqilgan preview (photo)
                msg = await bot.send_photo(
                    chat_id=chat_id,
                    photo=FSInputFile(image_path),
                    caption=caption,
                )
            except TelegramRetryAfter as e:
                if attempt == 0:
                    logger.warning("Rate limit chat_id={}, kutamiz {}s", chat_id, e.retry_after)
                    await asyncio.sleep(e.retry_after + 1)
                    continue
                await log_repo.log(
                    region_id=None, chat_id=chat_id, post_type=post_type,
                    status="error", error=f"retry_after exhausted: {e}",
                )
                return False
            except TelegramForbiddenError as e:
                await log_repo.log(
                    region_id=None, chat_id=chat_id, post_type=post_type,
                    status="blocked", error=str(e),
                )
                logger.error("Bot Qashqadaryo chatdan bloklangan: {}", chat_id)
                return False
            except (TelegramBadRequest, Exception) as e:
                await log_repo.log(
                    region_id=None, chat_id=chat_id, post_type=post_type,
                    status="error", error=str(e),
                )
                logger.error("Qashqadaryo send fail chat_id={}: {}", chat_id, e)
                return False

            await log_repo.log(
                region_id=None, chat_id=chat_id, post_type=post_type,
                status="ok", message_id=msg.message_id,
            )

            # 2) HD original fayl (document) — siqishsiz, to'liq caption bilan
            try:
                await bot.send_document(
                    chat_id=chat_id,
                    document=FSInputFile(image_path, filename=f"HD_{filename}"),
                    caption=caption,
                )
            except Exception as e:
                logger.warning("HD document yuborilmadi chat_id={}: {}", chat_id, e)

            return True
    return False


__all__ = [
    "build_qashqadaryo_image",
    "default_caption",
    "publish_existing_image",
    "run_qashqadaryo_post",
    "send_qashqadaryo_post",
]
