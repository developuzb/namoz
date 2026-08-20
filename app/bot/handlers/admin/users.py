"""Admin: user management — list, ban/unban, view subscriptions."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters import AdminFilter
from app.bot.keyboards.callback_data import (
    CB_ADMIN_ROOT,
    CB_ADMIN_USERS,
    CB_USR_BLOCK,
    CB_USR_PAGE,
    CB_USR_UNBLOCK,
    CB_USR_VIEW,
)
from app.core.logger import logger
from app.db.models.user import User
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.db.repositories.user_repo import UserRepository
from app.utils.text_utils import escape_html

router = Router(name="admin.users")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

#: Bir sahifaga maksimal user soni
PAGE_SIZE = 8


def _list_keyboard(users: list[User], *, page: int, has_more: bool):
    kb = InlineKeyboardBuilder()
    for u in users:
        mark = "🚫" if u.is_blocked else "✅"
        admin_mark = " 👑" if u.is_admin else ""
        label = f"{mark}{admin_mark} {u.full_name or '?'} (@{u.username or '—'})"
        kb.button(text=label[:60], callback_data=f"{CB_USR_VIEW}:{u.id}")

    # Paginatsiya tugmalari
    nav = []
    if page > 0:
        nav.append(("« Oldingi", f"{CB_USR_PAGE}:{page - 1}"))
    if has_more:
        nav.append(("Keyingi »", f"{CB_USR_PAGE}:{page + 1}"))
    for label, cb in nav:
        kb.button(text=label, callback_data=cb)

    kb.button(text="« Admin paneli", callback_data=CB_ADMIN_ROOT)

    sizes = [1] * len(users)
    if nav:
        sizes.append(len(nav))
    sizes.append(1)
    kb.adjust(*sizes)
    return kb.as_markup()


def _detail_keyboard(user_id: int, is_blocked: bool):
    kb = InlineKeyboardBuilder()
    if is_blocked:
        kb.button(text="✅ Blokdan chiqarish", callback_data=f"{CB_USR_UNBLOCK}:{user_id}")
    else:
        kb.button(text="🚫 Bloklash", callback_data=f"{CB_USR_BLOCK}:{user_id}")
    kb.button(text="« Userlar ro'yxati", callback_data=CB_ADMIN_USERS)
    kb.adjust(1)
    return kb.as_markup()


async def _show_users_page(
    call: CallbackQuery, session: AsyncSession, *, page: int = 0
) -> None:
    offset = page * PAGE_SIZE
    stmt = (
        select(User)
        .order_by(desc(User.created_at))
        .offset(offset)
        .limit(PAGE_SIZE + 1)
    )
    result = await session.execute(stmt)
    rows = list(result.scalars().all())
    has_more = len(rows) > PAGE_SIZE
    users = rows[:PAGE_SIZE]

    if not users and page == 0:
        await call.message.edit_text(
            "👥 Foydalanuvchi yo'q.",
            reply_markup=_list_keyboard([], page=0, has_more=False),
        )
        await call.answer()
        return

    text = (
        f"👥 <b>Foydalanuvchilar</b> — sahifa {page + 1}\n\n"
        "<i>✅ aktiv · 🚫 bloklangan · 👑 admin</i>"
    )
    await call.message.edit_text(
        text,
        reply_markup=_list_keyboard(users, page=page, has_more=has_more),
    )
    await call.answer()


@router.callback_query(F.data == CB_ADMIN_USERS)
async def show_users(call: CallbackQuery, session: AsyncSession) -> None:
    await _show_users_page(call, session, page=0)


@router.callback_query(F.data.startswith(f"{CB_USR_PAGE}:"))
async def page_users(call: CallbackQuery, session: AsyncSession) -> None:
    try:
        page = int(call.data.split(":")[-1])
    except (ValueError, IndexError):
        await call.answer("Noto'g'ri", show_alert=True)
        return
    await _show_users_page(call, session, page=page)


@router.callback_query(F.data.startswith(f"{CB_USR_VIEW}:"))
async def view_user(call: CallbackQuery, session: AsyncSession) -> None:
    try:
        uid = int(call.data.split(":")[-1])
    except (ValueError, IndexError):
        await call.answer("Noto'g'ri", show_alert=True)
        return

    user_repo = UserRepository(session)
    sub_repo = SubscriptionRepository(session)
    u = await user_repo.get(uid)
    if u is None:
        await call.answer("User topilmadi", show_alert=True)
        return

    subs = await sub_repo.list_by_user(u.id)
    sub_lines = "\n".join(
        f"  • {escape_html(s.region.name)}"
        + ("" if s.daily_post else " (post off)")
        + ("" if s.notify_farz else " (farz off)")
        for s in subs
    ) or "  <i>—</i>"

    text = (
        f"👤 <b>{escape_html(u.full_name or '—')}</b>\n\n"
        f"🆔 ID: <code>{u.id}</code>\n"
        f"📞 tg_id: <code>{u.tg_id}</code>\n"
        f"🌐 @{escape_html(u.username or '—')}\n"
        f"🗣 Til: <code>{u.language}</code>\n"
        f"📅 Qachon: <code>{u.created_at:%Y-%m-%d}</code>\n"
        f"🌙 Tinch soatlar: {'✅' if u.quiet_hours_enabled else '⬜'}\n"
        f"📊 Holat: {'🚫 bloklangan' if u.is_blocked else '✅ aktiv'}"
        f"{' · 👑 admin' if u.is_admin else ''}\n\n"
        f"<b>Obunalar ({len(subs)}):</b>\n{sub_lines}"
    )
    await call.message.edit_text(
        text, reply_markup=_detail_keyboard(u.id, u.is_blocked),
    )
    await call.answer()


@router.callback_query(F.data.startswith(f"{CB_USR_BLOCK}:"))
async def block_user(call: CallbackQuery, session: AsyncSession) -> None:
    try:
        uid = int(call.data.split(":")[-1])
    except (ValueError, IndexError):
        await call.answer("Noto'g'ri", show_alert=True)
        return

    user_repo = UserRepository(session)
    u = await user_repo.get(uid)
    if u is None:
        await call.answer("User topilmadi", show_alert=True)
        return

    u.is_blocked = True
    await session.flush()
    logger.info("User blocked by admin: tg_id={}", u.tg_id)
    await call.answer("🚫 Bloklandi")
    await view_user(call, session)


@router.callback_query(F.data.startswith(f"{CB_USR_UNBLOCK}:"))
async def unblock_user(call: CallbackQuery, session: AsyncSession) -> None:
    try:
        uid = int(call.data.split(":")[-1])
    except (ValueError, IndexError):
        await call.answer("Noto'g'ri", show_alert=True)
        return

    user_repo = UserRepository(session)
    u = await user_repo.get(uid)
    if u is None:
        await call.answer("User topilmadi", show_alert=True)
        return

    u.is_blocked = False
    await session.flush()
    logger.info("User unblocked by admin: tg_id={}", u.tg_id)
    await call.answer("✅ Blokdan chiqarildi")
    await view_user(call, session)
