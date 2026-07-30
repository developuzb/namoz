"""Telegram'ga xavfsiz yuborish — retry, log va blok bilan ishlash.

`daily_post` va `qashqadaryo_post` joblari uchun umumiy modul:
avval ikkalasida bir xil ~65 qatorlik nusxa bor edi.
"""
from __future__ import annotations

import asyncio

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.types import FSInputFile, Message

from app.core.logger import logger
from app.db.repositories.post_log_repo import PostLogRepository
from app.db.repositories.user_repo import UserRepository


async def send_photo_safe(
    *,
    bot: Bot,
    chat_id: int,
    image_path: str,
    caption: str,
    log_repo: PostLogRepository,
    post_type: str,
    region_id: int | None = None,
    user_repo: UserRepository | None = None,
) -> Message | None:
    """Photo yuboradi va natijani `post_logs` ga yozadi.

    - `TelegramRetryAfter` → talab qilingan vaqt kutilib, 1 marta qayta urinish
    - `TelegramForbiddenError` → `user_repo` berilgan bo'lsa user bloklangan deb belgilanadi
    - Boshqa xatolar → log + post_logs "error"

    Returns:
        Yuborilgan `Message` yoki `None` (muvaffaqiyatsiz).
    """
    for attempt in range(2):
        try:
            msg = await bot.send_photo(
                chat_id=chat_id,
                photo=FSInputFile(image_path),
                caption=caption,
            )
        except TelegramRetryAfter as e:
            if attempt == 0:
                logger.warning(
                    "Rate limit chat_id={}, kutamiz {}s", chat_id, e.retry_after,
                )
                await asyncio.sleep(e.retry_after + 1)
                continue
            await log_repo.log(
                region_id=region_id, chat_id=chat_id, post_type=post_type,
                status="error", error=f"retry_after exhausted: {e}",
            )
            return None
        except TelegramForbiddenError as e:
            if user_repo is not None:
                await user_repo.mark_blocked(chat_id)
            await log_repo.log(
                region_id=region_id, chat_id=chat_id, post_type=post_type,
                status="blocked", error=str(e),
            )
            logger.warning("Bloklangan: chat_id={}", chat_id)
            return None
        except TelegramBadRequest as e:
            await log_repo.log(
                region_id=region_id, chat_id=chat_id, post_type=post_type,
                status="error", error=str(e),
            )
            logger.error("Send fail chat_id={}: {}", chat_id, e)
            return None
        except Exception as e:  # noqa: BLE001
            await log_repo.log(
                region_id=region_id, chat_id=chat_id, post_type=post_type,
                status="error", error=str(e),
            )
            logger.exception("Send unexpected error chat_id={}: {}", chat_id, e)
            return None

        await log_repo.log(
            region_id=region_id, chat_id=chat_id, post_type=post_type,
            status="ok", message_id=msg.message_id,
        )
        return msg
    return None


async def notify_admins(bot: Bot, text: str) -> None:
    """Barcha adminlarga (ADMIN_IDS) xabar yuboradi.

    Xatolarni yutadi — job to'xtamasin. ADMIN_IDS bo'sh bo'lsa faqat log.
    """
    from app.core.config import get_settings

    admin_ids = get_settings().admin_ids_list
    if not admin_ids:
        logger.warning("notify_admins: ADMIN_IDS bo'sh — xabar yuborilmadi")
        return
    for admin_id in admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=text)
        except Exception as e:
            logger.warning("Admin {} ga ogohlantirish yuborilmadi: {}", admin_id, e)


async def send_document_safe(
    *,
    bot: Bot,
    chat_id: int,
    file_path: str,
    caption: str | None = None,
    filename: str | None = None,
) -> bool:
    """Document (HD fayl) yuboradi — rate limit'da 1 marta qayta urinadi."""
    for attempt in range(2):
        try:
            await bot.send_document(
                chat_id=chat_id,
                document=FSInputFile(file_path, filename=filename),
                caption=caption,
            )
            return True
        except TelegramRetryAfter as e:
            if attempt == 0:
                logger.warning(
                    "Rate limit (document) chat_id={}, kutamiz {}s",
                    chat_id, e.retry_after,
                )
                await asyncio.sleep(e.retry_after + 1)
                continue
            logger.warning("Document yuborilmadi (retry tugadi) chat_id={}", chat_id)
            return False
        except Exception as e:  # noqa: BLE001
            logger.warning("Document yuborilmadi chat_id={}: {}", chat_id, e)
            return False
    return False


__all__ = ["notify_admins", "send_document_safe", "send_photo_safe"]
