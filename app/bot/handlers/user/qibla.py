"""Qibla yo'nalishini ko'rsatish — kompas rasmi DM ga yuboriladi."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.callback_data import CB_QIBLA
from app.core.logger import logger
from app.db.models.user import User
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.services.qibla import make_qibla_image
from app.utils.text_utils import escape_html

router = Router(name="user.qibla")


@router.callback_query(F.data == CB_QIBLA)
async def show_qibla(
    call: CallbackQuery, user: User, session: AsyncSession
) -> None:
    sub_repo = SubscriptionRepository(session)
    user_subs = await sub_repo.list_by_user(user.id)

    if not user_subs:
        await call.answer("Avval hudud tanlang", show_alert=True)
        return

    # Birinchi obuna hududi koordinatasini ishlatamiz
    region = user_subs[0].region
    if region.latitude is None or region.longitude is None:
        await call.answer(
            f"⚠️ {region.name} uchun koordinata yo'q. "
            "Lokatsiya orqali yangi hudud qo'shing.",
            show_alert=True,
        )
        return

    await call.answer("⏳ Qibla hisoblanmoqda...")

    try:
        img_path, bearing, distance = make_qibla_image(
            region_name=region.name,
            latitude=region.latitude,
            longitude=region.longitude,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Qibla image fail: {}", e)
        await call.bot.send_message(
            chat_id=user.tg_id,
            text=f"❌ Qibla rasmi yasalmadi: <code>{escape_html(str(e))}</code>",
        )
        return

    caption = (
        f"🧭 <b>Qibla yo'nalishi</b> — {escape_html(region.name)}\n\n"
        f"📐 Azimuth: <code>{bearing:.1f}°</code> (true north'dan)\n"
        f"🕋 Ka'bagacha: <b>{distance:,.0f} km</b>\n\n"
        "<i>Kompas yoki telefondagi qibla ilovasini ishlatib, "
        "ko'rsatilgan burchakka yuzlaning.</i>\n\n"
        "<i>Eslatma: bu yo'nalish geodezik (great-circle), shu sababli "
        "uzoq joylarda taxminan to'g'ri yo'nalishni ko'rsatadi.</i>"
    )

    await call.bot.send_photo(
        chat_id=user.tg_id,
        photo=FSInputFile(img_path),
        caption=caption,
    )
    logger.info(
        "Qibla: tg_id={} region={} bearing={:.1f}° dist={:.0f}km",
        user.tg_id, region.name, bearing, distance,
    )
