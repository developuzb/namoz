"""Telegram kanallari uchun professional nom (Title) va tavsif (Description) yaratish hamda o'rnatish servisi."""
from __future__ import annotations

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.db.models.channel import Channel


def build_channel_metadata(channel: Channel) -> tuple[str, str]:
    """Kanal uchun professional nom (title) va tavsif (description) yasaydi."""
    region_name = channel.region.name if channel.region else "O'zbekiston"

    # 1. Professional Title (Nom)
    # Maksimal 128 belgi (Telegram cheklovi)
    title = f"📍 {region_name} | Namoz vaqtlari"

    # 2. Professional Description (Tavsif / Bio)
    # Maksimal 255 belgi (Telegram tavsif cheklovi)
    description = (
        f"🕌 {region_name} tumani bo'yicha kunlik aniq namoz vaqtlari, "
        "eslatmalar va taqvim rasmiy kanali.\n\n"
        "📅 Har kuni avtomatik yangilanish.\n"
        "🤖 Bot: @Taqvimbot\n"
        "✨ Ibodatlaringizni o'z vaqtida ado eting!"
    )

    # Telegram description limit check (255 chars)
    if len(description) > 255:
        description = description[:252] + "..."

    return title, description


async def update_channel_info(
    bot: Bot, channel: Channel, session: AsyncSession | None = None
) -> tuple[bool, str]:
    """Bitta kanal uchun nom va tavsifni Telegram'da yangilaydi va DB ga saqlaydi."""
    title, description = build_channel_metadata(channel)
    errors = []

    # 1. Nomni o'zgartirish (set_chat_title)
    try:
        await bot.set_chat_title(chat_id=channel.chat_id, title=title)
        if session:
            channel.title = title
            await session.flush()
    except Exception as e:
        err = f"Nomni o'zgartirishda xato: {e}"
        logger.warning(err)
        errors.append(err)

    # 2. Tavsifni o'zgartirish (set_chat_description)
    try:
        await bot.set_chat_description(chat_id=channel.chat_id, description=description)
    except Exception as e:
        err = f"Tavsifni o'zgartirishda xato: {e}"
        logger.warning(err)
        errors.append(err)

    if errors:
        return False, " | ".join(errors)

    logger.info("Kanal nomi va tavsifi yangilandi: chat_id={} ({})", channel.chat_id, title)
    return True, "OK"
