"""Admin: broadcast — barcha aktiv kanallarga va userlarga xabar yuborish.

Tizim imkoniyatlari:
  1. Nishonni tanlash: Kanallarga yoki Userlarga
  2. Barcha turdagi kontentlar (matn, rasm, video, hujjat, audio, animation/GIF, voice...)
  3. Interaktiv sozlamalar (ON/OFF):
     - 📌 Auto-caption (Kanal nomi va havola qo'shish)
     - 🔘 Obuna bo'lish tugmasi (Inline URL button)
     - 📝 Custom shablon (Kanalga xos matn)
  4. copy_message orqali avtomatik formatlash va forward belgisiz yuborish.
"""
from __future__ import annotations

import asyncio
from html import escape

from aiogram import F, Router
from aiogram.exceptions import (
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters import AdminFilter
from app.bot.keyboards import (
    admin_panel_keyboard,
    broadcast_preview_keyboard,
    broadcast_target_keyboard,
)
from app.bot.keyboards.callback_data import (
    CB_ADMIN_BROADCAST,
    CB_BC_CANCEL,
    CB_BC_CONFIRM,
    CB_BC_TARGET,
    CB_BC_TOGGLE,
)
from app.bot.states.admin import BroadcastFSM
from app.core.logger import logger
from app.db.models.channel import Channel
from app.db.repositories.channel_repo import ChannelRepository
from app.db.repositories.post_log_repo import PostLogRepository
from app.db.repositories.user_repo import UserRepository

router = Router(name="admin.broadcast")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

#: Telegram broadcast rate limit — 30 msg/sec global. 0.05s = 20 msg/sec.
_SEND_DELAY = 0.05


# =================== Helpers ===================

def _normalize_link(link: str | None) -> str | None:
    if not link:
        return None
    link = link.strip()
    if link.startswith("http://") or link.startswith("https://"):
        return link
    if link.startswith("@"):
        return f"https://t.me/{link[1:]}"
    return f"https://t.me/{link}"


def _build_channel_caption(
    orig_caption: str | None,
    channel: Channel,
    *,
    auto_link: bool,
    custom_template: bool,
) -> str | None:
    text = orig_caption or ""

    if custom_template and channel.custom_caption_template:
        tmpl = channel.custom_caption_template
        text = (
            tmpl.replace("{text}", text)
            .replace("{title}", escape(channel.title or ""))
            .replace("{link}", channel.link or "")
        )

    if auto_link:
        title_str = f"📌 <b>{escape(channel.title or 'Kanal')}</b>" if channel.title else ""
        link = _normalize_link(channel.link)
        link_str = f"🔗 {link}" if link else ""

        footer_parts = [p for p in (title_str, link_str) if p]
        if footer_parts:
            footer = "\n".join(footer_parts)
            text = f"{text}\n\n{footer}".strip() if text else footer

    return text or None


def _build_channel_keyboard(
    channel: Channel, *, sub_button: bool
) -> InlineKeyboardMarkup | None:
    if not sub_button:
        return None
    link = _normalize_link(channel.link)
    if not link:
        return None

    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Kanalga obuna bo'lish", url=link)
    return kb.as_markup()


# =================== Entry & Target Selection ===================

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "📨 <b>Broadcast bo'limi</b>\n\n"
        "Xabar yubormoqchi bo'lgan nishonni tanlang:",
        reply_markup=broadcast_target_keyboard(),
    )


@router.callback_query(F.data == CB_ADMIN_BROADCAST)
async def cb_broadcast(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(
        "📨 <b>Broadcast bo'limi</b>\n\n"
        "Xabar yubormoqchi bo'lgan nishonni tanlang:",
        reply_markup=broadcast_target_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data.startswith(f"{CB_BC_TARGET}:"))
async def cb_select_target(call: CallbackQuery, state: FSMContext) -> None:
    target = call.data.split(":")[-1]  # "channels" | "users"
    await state.set_state(BroadcastFSM.composing)
    await state.update_data(
        target=target,
        auto_link=True,
        sub_button=True,
        custom_template=False,
    )

    target_name = "📢 Kanallarga" if target == "channels" else "👥 Foydalanuvchilarga"
    text = (
        f"📨 <b>Broadcast — {target_name} yuborish</b>\n\n"
        "Jo'natmoqchi bo'lgan xabaringizni shu yerga yuboring.\n\n"
        "<i>Matn, rasm, video, fayl, ovozli xabar — har qanday kontent bo'lishi mumkin. "
        "HTML formatlash qo'llab-quvvatlanadi.</i>\n\n"
        "Bekor qilish: /cancel"
    )
    await call.message.edit_text(text)
    await call.answer()


# =================== Compose → Preview ===================

@router.message(StateFilter(BroadcastFSM.composing))
async def receive_broadcast(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    if message.text and message.text.startswith("/"):
        return

    data = await state.get_data()
    target = data.get("target", "channels")

    ch_repo = ChannelRepository(session)
    user_repo = UserRepository(session)

    if target == "channels":
        active_items = await ch_repo.list_active_with_region()
        count_label = f"<b>{len(active_items)}</b> ta aktiv kanalga"
    else:
        active_users = await user_repo.list_active()
        count_label = f"<b>{len(active_users)}</b> ta aktiv userga"

    # html_text aiogram'да matn VA caption'ni ham qamraydi (text or caption).
    # Eski kod `caption_html` ishlatardi — aiogram 3.x'да bunday property yo'q,
    # rasm+caption yuborilganда AttributeError berib bot "jim qolar" edi.
    orig_caption = message.html_text if (message.text or message.caption) else None

    await state.update_data(
        from_chat_id=message.chat.id,
        message_id=message.message_id,
        orig_caption=orig_caption,
    )
    await state.set_state(BroadcastFSM.confirming)

    kb = broadcast_preview_keyboard(
        target=target,
        auto_link=data.get("auto_link", True),
        sub_button=data.get("sub_button", True),
        custom_template=data.get("custom_template", False),
    )

    await message.answer(
        f"⬆️ Yuqoridagi xabar {count_label} yuboriladi.\n\n"
        "Pastdagi tugmalar orqali xabar parametrlarini moslashtirishingiz mumkin:",
        reply_markup=kb,
    )


# =================== Interactive Toggles ===================

@router.callback_query(StateFilter(BroadcastFSM.confirming), F.data.startswith(f"{CB_BC_TOGGLE}:"))
async def cb_toggle_option(
    call: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    option = call.data.split(":")[-1]
    data = await state.get_data()

    target = data.get("target", "channels")
    auto_link = data.get("auto_link", True)
    sub_button = data.get("sub_button", True)
    custom_template = data.get("custom_template", False)

    if option == "target":
        target = "users" if target == "channels" else "channels"
    elif option == "auto_link":
        auto_link = not auto_link
    elif option == "sub_button":
        sub_button = not sub_button
    elif option == "custom_template":
        custom_template = not custom_template

    await state.update_data(
        target=target,
        auto_link=auto_link,
        sub_button=sub_button,
        custom_template=custom_template,
    )

    if target == "channels":
        ch_repo = ChannelRepository(session)
        count = len(await ch_repo.list_active_with_region())
        count_label = f"<b>{count}</b> ta aktiv kanalga"
    else:
        user_repo = UserRepository(session)
        count = len(await user_repo.list_active())
        count_label = f"<b>{count}</b> ta aktiv userga"

    kb = broadcast_preview_keyboard(
        target=target,
        auto_link=auto_link,
        sub_button=sub_button,
        custom_template=custom_template,
    )

    text = (
        f"⬆️ Xabar {count_label} yuborilishi belgilangan.\n\n"
        "Parametrlarni o'zgartirishingiz yoki yuborishni boshlashingiz mumkin:"
    )

    await call.message.edit_text(text, reply_markup=kb)
    await call.answer("O'zgartirildi")


# =================== Confirm Send ===================

@router.callback_query(StateFilter(BroadcastFSM.confirming), F.data == CB_BC_CONFIRM)
async def confirm_send(
    call: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()
    from_chat_id = data.get("from_chat_id")
    message_id = data.get("message_id")
    target = data.get("target", "channels")
    auto_link = data.get("auto_link", True)
    sub_button = data.get("sub_button", True)
    custom_template = data.get("custom_template", False)
    orig_caption = data.get("orig_caption")

    if not from_chat_id or not message_id:
        await call.answer("Sessiya tugadi, qaytadan boshlang", show_alert=True)
        await state.clear()
        return

    await state.clear()
    await call.message.edit_text(f"⏳ <b>Broadcast boshlandi ({target})...</b>")
    await call.answer()

    log_repo = PostLogRepository(session)
    sent, blocked, failed = 0, 0, 0

    if target == "channels":
        ch_repo = ChannelRepository(session)
        channels = await ch_repo.list_active_with_region()

        for ch in channels:
            if (sent + failed) > 0 and (sent + failed) % 20 == 0:
                await session.commit()

            caption = _build_channel_caption(
                orig_caption,
                ch,
                auto_link=auto_link,
                custom_template=custom_template,
            )
            reply_markup = _build_channel_keyboard(ch, sub_button=sub_button)

            try:
                await call.bot.copy_message(
                    chat_id=ch.chat_id,
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                    caption=caption,
                    parse_mode="HTML" if caption else None,
                    reply_markup=reply_markup,
                )
            except TelegramForbiddenError:
                await log_repo.log(
                    region_id=ch.region_id, chat_id=ch.chat_id,
                    post_type="channel_broadcast", status="blocked",
                )
                failed += 1
            except TelegramRetryAfter as e:
                logger.warning("Rate limit, kutamiz {}s", e.retry_after)
                await asyncio.sleep(e.retry_after + 1)
                try:
                    await call.bot.copy_message(
                        chat_id=ch.chat_id,
                        from_chat_id=from_chat_id,
                        message_id=message_id,
                        caption=caption,
                        parse_mode="HTML" if caption else None,
                        reply_markup=reply_markup,
                    )
                    await log_repo.log(
                        region_id=ch.region_id, chat_id=ch.chat_id,
                        post_type="channel_broadcast", status="ok",
                    )
                    sent += 1
                except Exception as e2:
                    await log_repo.log(
                        region_id=ch.region_id, chat_id=ch.chat_id,
                        post_type="channel_broadcast", status="error", error=str(e2),
                    )
                    failed += 1
            except Exception as e:
                logger.exception("Channel broadcast error chat_id={}: {}", ch.chat_id, e)
                await log_repo.log(
                    region_id=ch.region_id, chat_id=ch.chat_id,
                    post_type="channel_broadcast", status="error", error=str(e),
                )
                failed += 1
            else:
                await log_repo.log(
                    region_id=ch.region_id, chat_id=ch.chat_id,
                    post_type="channel_broadcast", status="ok",
                )
                sent += 1

            await asyncio.sleep(_SEND_DELAY)

        await session.commit()
        logger.info("📢 Kanallarga broadcast tugadi: sent={} failed={}", sent, failed)

        await call.message.answer(
            f"✅ <b>Kanallarga broadcast yakunlandi</b>\n\n"
            f"  • 📢 Muvaffaqiyatli yuborildi: <b>{sent}</b>\n"
            f"  • ❌ Xatolik / Yuborilmadi: <b>{failed}</b>\n"
            f"  • 📊 Jami kanallar: <b>{sent + failed}</b>",
            reply_markup=admin_panel_keyboard(),
        )

    else:
        # Userlarga yuborish
        user_repo = UserRepository(session)
        users = await user_repo.list_active()

        for user in users:
            if (sent + blocked + failed) > 0 and (sent + blocked + failed) % 50 == 0:
                await session.commit()

            try:
                await call.bot.copy_message(
                    chat_id=user.tg_id,
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                    caption=orig_caption,
                    parse_mode="HTML" if orig_caption else None,
                )
            except TelegramForbiddenError:
                await user_repo.mark_blocked(user.tg_id)
                await log_repo.log(
                    region_id=None, chat_id=user.tg_id,
                    post_type="user_broadcast", status="blocked",
                )
                blocked += 1
            except TelegramRetryAfter as e:
                logger.warning("Rate limit, kutamiz {}s", e.retry_after)
                await asyncio.sleep(e.retry_after + 1)
                try:
                    await call.bot.copy_message(
                        chat_id=user.tg_id,
                        from_chat_id=from_chat_id,
                        message_id=message_id,
                        caption=orig_caption,
                        parse_mode="HTML" if orig_caption else None,
                    )
                    await log_repo.log(
                        region_id=None, chat_id=user.tg_id,
                        post_type="user_broadcast", status="ok",
                    )
                    sent += 1
                except Exception as e2:
                    await log_repo.log(
                        region_id=None, chat_id=user.tg_id,
                        post_type="user_broadcast", status="error", error=str(e2),
                    )
                    failed += 1
            except Exception as e:
                logger.exception("User broadcast error tg_id={}: {}", user.tg_id, e)
                await log_repo.log(
                    region_id=None, chat_id=user.tg_id,
                    post_type="user_broadcast", status="error", error=str(e),
                )
                failed += 1
            else:
                await log_repo.log(
                    region_id=None, chat_id=user.tg_id,
                    post_type="user_broadcast", status="ok",
                )
                sent += 1

            await asyncio.sleep(_SEND_DELAY)

        await session.commit()
        logger.info("👥 Userlarga broadcast tugadi: sent={} blocked={} failed={}", sent, blocked, failed)

        await call.message.answer(
            f"✅ <b>Foydalanuvchilarga broadcast yakunlandi</b>\n\n"
            f"  • ✅ Yuborildi: <b>{sent}</b>\n"
            f"  • 🚫 Bloklangan: <b>{blocked}</b>\n"
            f"  • ❌ Xatolik: <b>{failed}</b>\n"
            f"  • 📊 Jami: <b>{sent + blocked + failed}</b>",
            reply_markup=admin_panel_keyboard(),
        )


# =================== Cancel ===================

@router.callback_query(StateFilter(BroadcastFSM.confirming), F.data == CB_BC_CANCEL)
async def cancel_via_button(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(
        "❌ Broadcast bekor qilindi.\n\n👑 <b>Admin paneli</b>",
        reply_markup=admin_panel_keyboard(),
    )
    await call.answer()


@router.message(Command("cancel"), StateFilter(BroadcastFSM))
async def cancel_via_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "❌ Broadcast bekor qilindi.\n\n👑 <b>Admin paneli</b>",
        reply_markup=admin_panel_keyboard(),
    )
