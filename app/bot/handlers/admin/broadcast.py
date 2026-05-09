"""Admin: broadcast — barcha aktiv userlarga xabar yuborish.

Ikki bosqichli tasdiq bilan:
  1. /broadcast yoki 📨 tugma → admin xabar yuboradi (text/photo/video — har qanday)
  2. Bot preview + count'ni ko'rsatadi → [✅ Yuborish] [❌ Bekor]
  3. Tasdiq → barcha aktiv userlarga `bot.copy_message` orqali yuboriladi
  4. Final natija: sent / blocked / failed sonlari

`bot.copy_message` har qanday content turini (text, photo, video, ...)
forward'siz nusxa qiladi — `forwarded from` belgisi chiqmaydi.
"""
from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters import AdminFilter
from app.bot.keyboards import (
    admin_panel_keyboard,
    broadcast_confirm_keyboard,
)
from app.bot.keyboards.callback_data import (
    CB_ADMIN_BROADCAST,
    CB_BC_CANCEL,
    CB_BC_CONFIRM,
)
from app.bot.states.admin import BroadcastFSM
from app.core.logger import logger
from app.db.models.user import User
from app.db.repositories.post_log_repo import PostLogRepository
from app.db.repositories.user_repo import UserRepository

router = Router(name="admin.broadcast")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

#: Telegram broadcast rate limit — 30 msg/sec global. 0.05s = 20 msg/sec.
_SEND_DELAY = 0.05


# =================== Entry ===================

async def _start_compose(target: Message | CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BroadcastFSM.composing)
    text = (
        "📨 <b>Broadcast</b>\n\n"
        "Barcha aktiv userlarga jo'natmoqchi bo'lgan xabarni shu yerga yuboring.\n\n"
        "<i>Matn, rasm, video — har qanday turdagi kontent bo'lishi mumkin. "
        "HTML formatlash qabul qilinadi.</i>\n\n"
        "Bekor qilish: /cancel"
    )
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text)
        await target.answer()
    else:
        await target.answer(text)


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext) -> None:
    await _start_compose(message, state)


@router.callback_query(F.data == CB_ADMIN_BROADCAST)
async def cb_broadcast(call: CallbackQuery, state: FSMContext) -> None:
    await _start_compose(call, state)


# =================== Compose → Preview ===================

@router.message(StateFilter(BroadcastFSM.composing))
async def receive_broadcast(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    if message.text and message.text.startswith("/"):
        return  # /cancel boshqa handler'ga ketadi

    user_repo = UserRepository(session)
    active_users = await user_repo.list_active()
    active_count = len(active_users)

    await state.update_data(
        from_chat_id=message.chat.id,
        message_id=message.message_id,
        active_count=active_count,
    )
    await state.set_state(BroadcastFSM.confirming)

    await message.answer(
        f"⬆️ Yuqoridagi xabar <b>{active_count}</b> ta aktiv userga yuboriladi.\n\n"
        "Tasdiqlaysizmi?",
        reply_markup=broadcast_confirm_keyboard(),
    )


# =================== Confirm / Cancel ===================

@router.callback_query(StateFilter(BroadcastFSM.confirming), F.data == CB_BC_CONFIRM)
async def confirm_send(
    call: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()
    from_chat_id = data.get("from_chat_id")
    message_id = data.get("message_id")

    if not from_chat_id or not message_id:
        await call.answer("Sessiya tugadi", show_alert=True)
        await state.clear()
        return

    await state.clear()
    await call.message.edit_text("⏳ <b>Broadcast boshlandi...</b>")
    await call.answer()

    user_repo = UserRepository(session)
    log_repo = PostLogRepository(session)
    users = await user_repo.list_active()

    sent = 0
    blocked = 0
    failed = 0

    for user in users:
        # Periodik commit — uzun broadcast paytida progress saqlash
        if (sent + blocked + failed) > 0 and (sent + blocked + failed) % 50 == 0:
            await session.commit()

        try:
            await call.bot.copy_message(
                chat_id=user.tg_id,
                from_chat_id=from_chat_id,
                message_id=message_id,
            )
        except TelegramForbiddenError:
            await user_repo.mark_blocked(user.tg_id)
            await log_repo.log(
                region_id=None, chat_id=user.tg_id,
                post_type="broadcast", status="blocked",
            )
            blocked += 1
        except TelegramRetryAfter as e:
            logger.warning("Rate limit, kutamiz {}s", e.retry_after)
            await asyncio.sleep(e.retry_after + 1)
            # Re-try this user once
            try:
                await call.bot.copy_message(
                    chat_id=user.tg_id,
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                )
                await log_repo.log(
                    region_id=None, chat_id=user.tg_id,
                    post_type="broadcast", status="ok",
                )
                sent += 1
            except Exception as e2:
                await log_repo.log(
                    region_id=None, chat_id=user.tg_id,
                    post_type="broadcast", status="error", error=str(e2),
                )
                failed += 1
            continue
        except TelegramBadRequest as e:
            await log_repo.log(
                region_id=None, chat_id=user.tg_id,
                post_type="broadcast", status="error", error=str(e),
            )
            failed += 1
        except Exception as e:
            logger.exception("Broadcast unexpected error tg={}: {}", user.tg_id, e)
            await log_repo.log(
                region_id=None, chat_id=user.tg_id,
                post_type="broadcast", status="error", error=str(e),
            )
            failed += 1
        else:
            await log_repo.log(
                region_id=None, chat_id=user.tg_id,
                post_type="broadcast", status="ok",
            )
            sent += 1

        await asyncio.sleep(_SEND_DELAY)

    logger.info(
        "📨 Broadcast tugadi: sent={} blocked={} failed={}",
        sent, blocked, failed,
    )

    await call.message.answer(
        f"✅ <b>Broadcast yakunlandi</b>\n\n"
        f"  • ✅ Yuborildi: <b>{sent}</b>\n"
        f"  • 🚫 Bloklangan: <b>{blocked}</b>\n"
        f"  • ❌ Xatolik: <b>{failed}</b>\n"
        f"  • 📊 Jami: <b>{sent + blocked + failed}</b>",
        reply_markup=admin_panel_keyboard(),
    )


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
