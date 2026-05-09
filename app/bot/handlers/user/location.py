"""Lokatsiya orqali hudud topish — yer yuzining istalgan joyida ishlaydi.

Oqim:
1. /start → "Lokatsiya orqali" → reply keyboard
2. User location yuboradi (Telegram native dialog)
3. Bot reverse-geocode qiladi (Nominatim)
4. DB da shu lat/lon ga eng yaqin region bormi tekshiradi (10 km radiusda)
   - Bor bo'lsa: tasdiqlash so'raydi
   - Yo'q bo'lsa: yangi region yaratadi (geocode nomi bilan), tasdiqlash so'raydi
5. User tasdiqlasa — obuna yaratiladi
"""
from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import (
    location_confirm_keyboard,
    location_request_keyboard,
    main_menu_keyboard,
    onboarding_keyboard,
    remove_keyboard,
)
from app.bot.keyboards.callback_data import (
    CB_LOC_CANCEL,
    CB_LOC_CONFIRM,
    CB_ONBOARD_LIST,
    CB_ONBOARD_LOCATION,
)
from app.core.constants import MAX_SUBSCRIPTIONS_PER_USER
from app.core.logger import logger
from app.db.models.region import Region
from app.db.models.user import User
from app.db.repositories.region_repo import RegionRepository
from app.db.repositories.stats_repo import StatsRepository
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.services.geocoding import GeocodingError, reverse_geocode
from app.utils.text_utils import escape_html

router = Router(name="user.location")

#: Mavjud regionga "yaqin" deb hisoblanadigan masofa (km)
_NEAR_RADIUS_KM = 15.0


# =================== Helpers ===================

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Ikki nuqta orasidagi masofa (km)."""
    r = 6371.0  # Earth radius
    lat1r, lat2r = radians(lat1), radians(lat2)
    dlat = lat2r - lat1r
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(lat1r) * cos(lat2r) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))


def _slugify(name: str) -> str:
    """Joy nomidan slug yasash. URL-safe, kichik harflar."""
    import re
    s = name.lower().strip()
    # O'zbekcha apostroflar va boshqalarni almashtirish
    s = s.replace("ʻ", "").replace("'", "").replace("ʼ", "").replace("`", "")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s or "loc"


async def _find_nearest_region(
    session: AsyncSession,
    *,
    lat: float,
    lon: float,
    max_km: float = _NEAR_RADIUS_KM,
) -> tuple[Region, float] | None:
    """
    DB dagi koordinatasi bor LEAF (sub-region'siz) regionlar ichidan eng yaqinini topadi.

    Parent region'lar (viloyatlar) chiqariladi — chunki user aniq joyni xohlaydi
    (Qashqadaryo viloyati emas, balki Qarshi tumani).

    Returns:
        (region, distance_km) yoki None — agar `max_km` ichida hech qaysi yo'q.
    """
    # Leaf regions = sub-regionsi yo'q regionlar
    parent_subq = (
        select(Region.parent_id)
        .where(Region.parent_id.is_not(None))
        .distinct()
    )
    stmt = select(Region).where(
        Region.is_active.is_(True),
        Region.latitude.is_not(None),
        Region.longitude.is_not(None),
        Region.id.not_in(parent_subq),
    )
    result = await session.execute(stmt)
    candidates = result.scalars().all()

    nearest: tuple[Region, float] | None = None
    for r in candidates:
        d = _haversine_km(lat, lon, r.latitude, r.longitude)  # type: ignore[arg-type]
        if nearest is None or d < nearest[1]:
            nearest = (r, d)

    if nearest is None or nearest[1] > max_km:
        return None
    return nearest


async def _create_region_from_geocode(
    session: AsyncSession,
    *,
    name: str,
    country: str | None,
    lat: float,
    lon: float,
) -> Region:
    """Yangi region yaratadi (slug konflikti bo'lsa raqam qo'shadi)."""
    rr = RegionRepository(session)
    base_slug = _slugify(name)
    slug = base_slug
    suffix = 2
    while await rr.get_by_slug(slug) is not None:
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    # Nom konflikti — _2 qo'shamiz
    base_name = name
    candidate_name = name
    n_suffix = 2
    while await rr.get_by_name(candidate_name) is not None:
        candidate_name = f"{base_name} ({n_suffix})"
        n_suffix += 1

    region = await rr.create(
        name=candidate_name,
        slug=slug,
        provider_name=None,
        praytime_id=None,
        parent_id=None,
        timezone="UTC",  # tz aniq emas — Aladhan UTC qabul qiladi va o'zi to'g'rilaydi
        latitude=lat,
        longitude=lon,
        country=country,
        is_active=True,
    )
    logger.info(
        "🆕 Region yaratildi: name={!r} slug={} ({:.4f}, {:.4f})",
        candidate_name, slug, lat, lon,
    )
    return region


# =================== Handlers ===================

@router.callback_query(F.data == CB_ONBOARD_LOCATION)
async def request_location(call: CallbackQuery) -> None:
    """Lokatsiya so'rovi reply keyboard'ini ko'rsatadi."""
    await call.message.answer(
        "📍 Quyidagi tugmani bosing va lokatsiyangizni yuboring.\n\n"
        "<i>Telegram sizdan ruxsat so'raydi. Koordinata DB'da saqlanmaydi — "
        "faqat eng yaqin hududni topish uchun ishlatiladi.</i>",
        reply_markup=location_request_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data == CB_ONBOARD_LIST)
async def use_list(call: CallbackQuery, session: AsyncSession) -> None:
    """Ro'yxatdan tanlash — viloyat keyboard'ga o'tadi."""
    from app.bot.handlers.user.regions import _show_viloyat_list

    await _show_viloyat_list(call, session)


@router.message(F.text == "❌ Bekor qilish")
async def cancel_location(
    call_or_msg: Message, user: User, session: AsyncSession
) -> None:
    sub_repo = SubscriptionRepository(session)
    sub_count = await sub_repo.count_by_user(user.id)
    await call_or_msg.answer(
        "Bekor qilindi.",
        reply_markup=remove_keyboard(),
    )
    await call_or_msg.answer(
        "Asosiy menyu:",
        reply_markup=main_menu_keyboard(has_subscriptions=sub_count > 0),
    )


@router.message(F.location)
async def handle_location(
    message: Message, user: User, session: AsyncSession
) -> None:
    """Foydalanuvchi lokatsiya yubordi — geocode qilamiz."""
    if user is None or message.location is None:
        return

    lat = message.location.latitude
    lon = message.location.longitude

    # Reply keyboard'ni olib tashlaymiz
    await message.answer(
        "🔎 Hudud aniqlanmoqda...",
        reply_markup=remove_keyboard(),
    )

    # 1. Avval DB'dan yaqin region qidirish
    nearest = await _find_nearest_region(session, lat=lat, lon=lon)

    if nearest is not None:
        region, distance = nearest
        text = (
            f"📍 Eng yaqin hudud topildi:\n\n"
            f"<b>{escape_html(region.name)}</b>"
            + (f", {escape_html(region.country)}" if region.country else "")
            + f"\n\nMasofa: <b>~{distance:.1f} km</b>\n\n"
            "Shu hududga obuna bo'lasizmi?"
        )
        await message.answer(
            text, reply_markup=location_confirm_keyboard(region.id)
        )
        logger.info(
            "Lokatsiya: tg_id={} -> mavjud region {!r} ({:.1f} km)",
            user.tg_id, region.name, distance,
        )
        return

    # 2. Yaqin region yo'q — Nominatim'dan nom olib yangi region yaratamiz
    try:
        loc = await reverse_geocode(lat, lon, language=user.language or "uz,en")
    except GeocodingError as e:
        logger.warning("Geocoding xato: {}", e)
        await message.answer(
            "⚠️ Lokatsiya nomini aniqlay olmadim. "
            "Boshqa usulda urinib ko'ring:",
            reply_markup=onboarding_keyboard(),
        )
        return

    region_name = loc.short_name
    if not region_name or region_name == "":
        await message.answer(
            "⚠️ Bu lokatsiya uchun joy nomi topilmadi.",
            reply_markup=onboarding_keyboard(),
        )
        return

    region = await _create_region_from_geocode(
        session,
        name=loc.city or region_name,
        country=loc.country,
        lat=lat,
        lon=lon,
    )
    await session.flush()  # region.id kerak

    text = (
        f"📍 Yangi hudud aniqlandi:\n\n"
        f"<b>{escape_html(region.name)}</b>"
        + (f", {escape_html(region.country)}" if region.country else "")
        + f"\n📌 <code>{lat:.4f}, {lon:.4f}</code>\n\n"
        "Obuna bo'lasizmi?"
    )
    await message.answer(text, reply_markup=location_confirm_keyboard(region.id))


@router.callback_query(F.data.startswith(f"{CB_LOC_CONFIRM}:"))
async def confirm_location_subscribe(
    call: CallbackQuery, user: User, session: AsyncSession
) -> None:
    try:
        region_id = int(call.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await call.answer("Noto'g'ri tugma", show_alert=True)
        return

    rr = RegionRepository(session)
    sub_repo = SubscriptionRepository(session)
    stats = StatsRepository(session)

    region = await rr.get(region_id)
    if not region:
        await call.answer("Hudud topilmadi", show_alert=True)
        return

    existing = await sub_repo.get_one(user.id, region_id)
    if existing:
        await call.answer("Allaqachon obunasiz", show_alert=True)
    else:
        sub_count = await sub_repo.count_by_user(user.id)
        if sub_count >= MAX_SUBSCRIPTIONS_PER_USER:
            await call.answer(
                f"⛔ Sizda allaqachon {MAX_SUBSCRIPTIONS_PER_USER} ta obuna bor.",
                show_alert=True,
            )
            return

        await sub_repo.create(user_id=user.id, region_id=region_id)
        await stats.track("subscribe", user_id=user.id, region_id=region_id)
        await call.answer(f"✅ {region.name} ga obuna bo'ldingiz")
        logger.info("Subscribe (location): tg_id={} region={}", user.tg_id, region.name)

    new_count = await sub_repo.count_by_user(user.id)
    await call.message.edit_text(
        f"✅ <b>{escape_html(region.name)}</b> ga obuna bo'ldingiz.\n\n"
        "Asosiy menyudan vaqtlarni ko'rishingiz mumkin:",
        reply_markup=main_menu_keyboard(has_subscriptions=new_count > 0),
    )


@router.callback_query(F.data == CB_LOC_CANCEL)
async def cancel_location_choice(call: CallbackQuery) -> None:
    await call.message.edit_text(
        "Hudud tanlash usulini tanlang:",
        reply_markup=onboarding_keyboard(),
    )
    await call.answer()
