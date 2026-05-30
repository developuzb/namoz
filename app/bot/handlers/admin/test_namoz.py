"""/test_namoz — admin uchun: Qashqadaryo plakatini preview va publish flow.

Flow:
  1) Admin `/test_namoz` yuboradi
  2) Bot 14 tuman vaqtlarini olib plakatni yasaydi va adminga **preview** yuboradi
     (faqat adminning chat'iga, kanalga emas)
  3) Admin shu preview xabariga `OK` deb reply qiladi
  4) Bot xuddi shu rasmni `NAMOZ_CHAT_ID` kanaliga yuboradi
  5) `OK` kelmasa kanalga hech narsa o'tmaydi
"""
from __future__ import annotations

import time
from datetime import date
from pathlib import Path

from aiogram import Router
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
)
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message

from app.bot.filters import AdminFilter
from app.core.config import get_settings
from app.core.exceptions import ProviderError
from app.core.logger import logger
from app.db.models.user import User
from app.scheduler.jobs.qashqadaryo_post import (
    build_qashqadaryo_image,
    publish_existing_image,
)

router = Router(name="admin.test_namoz")
router.message.filter(AdminFilter())

#: Tasdiqlash so'zlari (case-insensitive)
_OK_WORDS: set[str] = {"ok", "ok!", "okey", "okay", "ха", "ҳа", "ha", "+", "tasdiq"}

#: Preview cache — kalit (chat_id, message_id), qiymat: (image_path, target_date, ts)
#: TTL: 30 daqiqa. Kichik holat, in-memory yetadi.
_PREVIEW_CACHE: dict[tuple[int, int], tuple[Path, date, float]] = {}
_TTL_SECONDS = 30 * 60


def _prune_cache() -> None:
    now = time.time()
    stale = [k for k, (_, _, ts, *_) in _PREVIEW_CACHE.items() if now - ts > _TTL_SECONDS]
    for k in stale:
        _PREVIEW_CACHE.pop(k, None)


@router.message(Command("test_namoz"))
async def cmd_test_namoz(message: Message, user: User) -> None:
    """Plakatni admin chat'ga preview qilib yuboradi (kanalga emas)."""
    settings = get_settings()
    chat_id = settings.namoz_chat_id
    if not chat_id:
        await message.answer(
            "❌ <b>NAMOZ_CHAT_ID o'rnatilmagan</b>\n\n"
            "Plakat qaysi kanalga yuborilishini bilish uchun .env ga "
            "<code>NAMOZ_CHAT_ID=-100xxxxxxxxxx</code> qo'shing va botni "
            "qayta ishga tushiring.",
        )
        return

    notice = await message.answer(
        "⏳ 14 tuman uchun bugungi namoz vaqtlari olinmoqda…",
    )
    logger.info("/test_namoz: tg_id={} preview boshlandi", user.tg_id)

    target_date = date.today()
    try:
        image_path, regions_data, masjid = await build_qashqadaryo_image(
            target_date=target_date, test_mode=False,
        )
    except (ValueError, ProviderError) as e:
        logger.error("test_namoz: plakat yasalmadi: {}", e)
        try:
            await notice.delete()
        except Exception:
            pass
        await message.answer(
            f"❌ <b>Plakat yasalmadi</b>\n\n<code>{type(e).__name__}: {e}</code>",
        )
        return

    try:
        await notice.delete()
    except Exception:
        pass

    preview = await message.answer_photo(
        photo=FSInputFile(image_path),
        caption=(
            "🔍 <b>Plakat preview</b>\n\n"
            f"📅 <b>Sana:</b> {target_date.strftime('%d.%m.%Y')}\n"
            f"📢 <b>Kanal:</b> <code>{chat_id}</code>\n\n"
            "Tasdiqlash uchun ushbu xabarga <b>OK</b> deb javob bering. "
            "Aks holda kanalga hech narsa yuborilmaydi.\n\n"
            f"⏰ Tasdiqlash muddati: <i>{_TTL_SECONDS // 60} daqiqa</i>"
        ),
    )

    _prune_cache()
    _PREVIEW_CACHE[(message.chat.id, preview.message_id)] = (
        image_path, target_date, time.time(), masjid, regions_data,
    )


def _is_ok_text(text: str | None) -> bool:
    if not text:
        return False
    return text.strip().lower() in _OK_WORDS


async def _is_preview_reply(message: Message) -> bool:
    """Faqat preview xabariga reply bo'lsa True — filtr boshqa
    handlerlarni bloklamasligi uchun.
    """
    reply = message.reply_to_message
    if reply is None or not message.text:
        return False
    return (message.chat.id, reply.message_id) in _PREVIEW_CACHE


@router.message(_is_preview_reply)
async def on_preview_reply(message: Message, user: User) -> None:
    """Preview xabariga reply — `OK` bo'lsa kanalga yuboriladi."""
    reply = message.reply_to_message
    if reply is None:
        return

    key = (message.chat.id, reply.message_id)

    if not _is_ok_text(message.text):
        await message.reply(
            "ℹ️ Tasdiqlash uchun <b>OK</b> deb yozing. "
            "Boshqa matn yuborilmadi degani.",
        )
        return

    # OK keldi — kanalga yuboramiz
    image_path, target_date, _ts, masjid, regions_data = _PREVIEW_CACHE.pop(key)
    settings = get_settings()
    chat_id = settings.namoz_chat_id
    if not chat_id:
        await message.reply(
            "❌ NAMOZ_CHAT_ID hozir o'rnatilmagan — yuborilmadi.",
        )
        return

    logger.info(
        "test_namoz: tg_id={} tasdiqladi → kanal {} ga yuborilmoqda",
        user.tg_id, chat_id,
    )

    status = await message.reply("📤 Kanalga yuborilmoqda…")

    try:
        ok = await publish_existing_image(
            message.bot,
            chat_id=chat_id,
            image_path=str(image_path),
            target_date=target_date,
            masjid_times=masjid or None,
            regions_data=regions_data or None,
        )
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        ok = False
        logger.exception("test_namoz publish xato: {}", e)

    try:
        await status.delete()
    except Exception:
        pass

    if ok:
        await message.reply(
            f"✅ <b>Yuborildi</b>\n\n"
            f"Plakat <code>{chat_id}</code> kanaliga muvaffaqiyatli "
            f"joylandi.",
        )
    else:
        await message.reply(
            "❌ <b>Yuborilmadi</b>\n\n"
            "Loglarni tekshiring: bot kanalda admin emasligi, kanal "
            "ID xato, yoki Telegram cheklovi.",
        )
