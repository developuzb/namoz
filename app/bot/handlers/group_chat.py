"""Guruh chatlar uchun handlerlar — /subscribe, /unsubscribe, my_chat_member.

Bot guruhga qo'shilgach, admin /subscribe Qarshi bilan obuna qiladi.
Daily post (06:00) shu guruhga ham yuboriladi.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.types import ChatMemberUpdated, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError
from app.core.logger import logger
from app.db.models.region import Region
from app.db.models.subscribed_chat import SubscribedChat
from app.db.repositories.region_repo import RegionRepository
from app.db.repositories.subscribed_chat_repo import SubscribedChatRepository
from app.utils.text_utils import escape_html

router = Router(name="group_chat")

#: Faqat guruh / supergruh chatlar uchun
_GROUP_TYPES = {"group", "supergroup"}


# ============== Bot guruhga qo'shilgani / chiqarilgani ==============

@router.my_chat_member()
async def on_chat_member_update(
    event: ChatMemberUpdated, session: AsyncSession
) -> None:
    """Bot guruhga qo'shilgani / chiqarilganini kuzatish."""
    chat = event.chat
    if chat.type not in _GROUP_TYPES:
        return

    new_status = event.new_chat_member.status
    old_status = event.old_chat_member.status

    chat_repo = SubscribedChatRepository(session)
    existing = await chat_repo.get_by_chat_id(chat.id)

    # Bot qo'shildi (member yoki administrator)
    if new_status in {"member", "administrator"} and old_status in {"left", "kicked"}:
        logger.info(
            "Bot guruhga qo'shildi: chat_id={} title={!r} by={}",
            chat.id, chat.title, event.from_user.id if event.from_user else "?",
        )
        # Salom xabari
        try:
            await event.bot.send_message(
                chat.id,
                "👋 <b>Assalomu alaykum!</b>\n\n"
                "Men <b>TAQVIMbot</b> — namoz vaqtlari uchun bot.\n\n"
                "<b>Boshlash:</b>\n"
                "1️⃣ Mendan post yuborish ruxsatini bering (admin qiling)\n"
                "2️⃣ <code>/subscribe Qarshi</code> deb yozing — guruh "
                "shu hududga obuna bo'ladi\n\n"
                "<b>Komandalar:</b>\n"
                "  • /subscribe &lt;hudud&gt; — obuna bo'lish\n"
                "  • /unsubscribe — obunadan chiqish\n"
                "  • /regions — mavjud hududlar\n"
                "  • /today — bugungi vaqtlar (obuna bo'lganda)",
            )
        except TelegramBadRequest as e:
            logger.warning("Salom xabar yuborilmadi: {}", e)

    # Bot chiqarildi yoki bloklandi
    elif new_status in {"left", "kicked"} and old_status in {"member", "administrator"}:
        logger.info(
            "Bot guruhdan chiqarildi: chat_id={} title={!r}",
            chat.id, chat.title,
        )
        if existing:
            existing.is_active = False
            await session.flush()


# ============== /subscribe <slug> ==============

@router.message(Command("subscribe"), F.chat.type.in_(_GROUP_TYPES))
async def group_subscribe(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    if not await _is_chat_admin(message):
        await message.reply("⛔ Faqat guruh adminlari obuna qila oladi.")
        return

    if not command.args:
        await message.reply(
            "❓ Hudud nomini yoki slug'ini bering.\n\n"
            "Misol: <code>/subscribe Qarshi</code>\n\n"
            "Mavjud hududlar uchun: /regions"
        )
        return

    query = command.args.strip()

    # DB'da hudud qidirish (slug yoki name bo'yicha)
    rr = RegionRepository(session)
    region = await rr.get_by_slug(query.lower())
    if region is None:
        # Name bo'yicha
        stmt = (
            select(Region)
            .where(
                Region.is_active.is_(True),
                Region.name.ilike(f"%{query}%"),
            )
            .limit(1)
        )
        region = (await session.execute(stmt)).scalar_one_or_none()

    if region is None:
        await message.reply(
            f"😔 <b>{escape_html(query)}</b> bo'yicha hudud topilmadi.\n\n"
            "Mavjud ro'yxat: /regions"
        )
        return

    chat_repo = SubscribedChatRepository(session)
    existing = await chat_repo.get_by_chat_id(message.chat.id)

    if existing:
        # Region o'zgartirish
        old_region_id = existing.region_id
        existing.region_id = region.id
        existing.title = message.chat.title
        existing.is_active = True
        existing.added_by_tg_id = message.from_user.id if message.from_user else None
        await session.flush()
        if old_region_id == region.id:
            await message.reply(
                f"✅ Bu guruh allaqachon <b>{escape_html(region.name)}</b> ga obuna."
            )
        else:
            await message.reply(
                f"🔄 Obuna o'zgartirildi: <b>{escape_html(region.name)}</b>"
            )
    else:
        try:
            await chat_repo.create(
                chat_id=message.chat.id,
                title=message.chat.title,
                chat_type=message.chat.type,
                region_id=region.id,
                added_by_tg_id=message.from_user.id if message.from_user else None,
                daily_post=True,
                notify_farz=False,
                is_active=True,
            )
        except AlreadyExistsError as e:
            await message.reply(f"⚠️ Xato: {e}")
            return
        await message.reply(
            f"✅ <b>{escape_html(region.name)}</b> ga obuna bo'ldi!\n\n"
            "Har kuni 06:00 da kunlik post yuboriladi.\n"
            "Obunadan chiqish: /unsubscribe"
        )

    logger.info(
        "Group subscribe: chat_id={} region={} by tg_id={}",
        message.chat.id, region.name,
        message.from_user.id if message.from_user else "?",
    )


# ============== /unsubscribe ==============

@router.message(Command("unsubscribe"), F.chat.type.in_(_GROUP_TYPES))
async def group_unsubscribe(message: Message, session: AsyncSession) -> None:
    if not await _is_chat_admin(message):
        await message.reply("⛔ Faqat guruh adminlari obunani bekor qila oladi.")
        return

    chat_repo = SubscribedChatRepository(session)
    existing = await chat_repo.get_by_chat_id(message.chat.id)

    if existing is None or not existing.is_active:
        await message.reply("ℹ️ Bu guruh hech qaysi hududga obuna emas.")
        return

    await chat_repo.delete(existing)
    await message.reply(
        "✅ Obuna bekor qilindi. Bot guruhda qoladi, lekin endi "
        "kunlik post yubormaydi.\n\n"
        "Qaytadan obuna: <code>/subscribe Qarshi</code>"
    )
    logger.info("Group unsubscribe: chat_id={}", message.chat.id)


# ============== /regions ==============

@router.message(Command("regions"), F.chat.type.in_(_GROUP_TYPES))
async def group_list_regions(message: Message, session: AsyncSession) -> None:
    rr = RegionRepository(session)
    top = await rr.list_top_level()

    lines: list[str] = ["📍 <b>Mavjud hududlar:</b>\n"]

    # Guruhlangan: viloyat → tumanlar
    for parent in top:
        children = await rr.list_children(parent.id)
        if children:
            lines.append(f"\n<b>{escape_html(parent.name)}:</b>")
            for c in children:
                lines.append(
                    f"  • <code>/subscribe {c.slug}</code> — {escape_html(c.name)}"
                )
        else:
            # Flat region
            lines.append(
                f"  • <code>/subscribe {parent.slug}</code> — {escape_html(parent.name)}"
                + (f" ({escape_html(parent.country)})" if parent.country else "")
            )

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3990] + "\n...</b>"
    await message.reply(text)


# ============== /today ==============

@router.message(Command("today"), F.chat.type.in_(_GROUP_TYPES))
async def group_today(message: Message, session: AsyncSession) -> None:
    """Bu guruh obuna bo'lgan hudud uchun bugungi vaqtlarni yuborish."""
    chat_repo = SubscribedChatRepository(session)
    sub = await chat_repo.get_by_chat_id(message.chat.id)

    if sub is None or not sub.is_active:
        await message.reply(
            "ℹ️ Bu guruh hudud uchun obuna emas.\n\n"
            "Avval: <code>/subscribe Qarshi</code>"
        )
        return

    from datetime import date
    from aiogram.types import FSInputFile
    from app.services.registry import get_post_service

    notice = await message.reply("⏳ Vaqtlar tayyorlanmoqda...")
    try:
        bundle = await get_post_service().build_for_region(
            session=session, region=sub.region, target_date=date.today(),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Group post bundle fail chat={}: {}", message.chat.id, e)
        await notice.edit_text(f"❌ Xato: <code>{e}</code>")
        return

    try:
        await notice.delete()
    except Exception:  # noqa: BLE001
        pass

    await message.answer_photo(
        photo=FSInputFile(bundle.image_path),
        caption=bundle.caption,
    )


# ============== Yordam ==============

@router.message(Command("start"), F.chat.type.in_(_GROUP_TYPES))
async def group_start(message: Message, session: AsyncSession) -> None:
    chat_repo = SubscribedChatRepository(session)
    sub = await chat_repo.get_by_chat_id(message.chat.id)

    if sub and sub.is_active:
        await message.reply(
            f"👋 Bu guruh <b>{escape_html(sub.region.name)}</b> hududiga obuna.\n\n"
            "Komandalar:\n"
            "  • /today — bugungi vaqtlar\n"
            "  • /unsubscribe — obunani bekor qilish\n"
            "  • /regions — boshqa hududlar"
        )
    else:
        await message.reply(
            "👋 <b>Assalomu alaykum!</b>\n\n"
            "Bot guruhga qo'shildi, lekin hali hech qaysi hududga obuna emas.\n\n"
            "<b>Boshlash:</b>\n"
            "  • <code>/subscribe Qarshi</code> — guruhni obuna qilish\n"
            "  • /regions — mavjud hududlar ro'yxati"
        )


# ============== Helpers ==============

async def _is_chat_admin(message: Message) -> bool:
    """Foydalanuvchi shu guruhda admin yoki yo'qligini tekshiradi."""
    if message.from_user is None:
        return False
    try:
        admins = await message.bot.get_chat_administrators(message.chat.id)
    except TelegramBadRequest as e:
        logger.warning("get_chat_administrators fail: {}", e)
        return False
    return any(a.user.id == message.from_user.id for a in admins)
