"""WebApp uchun API endpointlari (JSON)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pytz
from aiohttp import web
from sqlalchemy import select

from app.core.config import get_settings
from app.core.constants import ALL_PRAYERS
from app.core.content import get_daily_ayah
from app.core.exceptions import ProviderError
from app.core.logger import logger
from app.db.models.region import Region
from app.db.repositories import (
    RegionRepository,
    SubscriptionRepository,
    UserRepository,
)
from app.db.session import get_session
from app.services.hijri_service import gregorian_to_hijri_uz
from app.services.qibla import calculate_qibla_bearing, calculate_qibla_distance_km
from app.services.registry import get_prayer_service
from app.services.time_calculator import calculate_nafl_windows
from app.web.auth import extract_user_id


async def _resolve_user_id(request: web.Request) -> int | None:
    """Request'dan user_id ni olish (initData orqali yoki ?tg_id= fallback)."""
    settings = get_settings()
    init_data = request.query.get("initData") or request.headers.get(
        "X-Telegram-Init-Data", "",
    )
    if init_data:
        uid = extract_user_id(init_data, settings.BOT_TOKEN)
        if uid is not None:
            return uid
    # Dev fallback — query param (production'da xavfsiz emas)
    try:
        return int(request.query.get("tg_id", "0")) or None
    except ValueError:
        return None


async def health(request: web.Request) -> web.Response:
    """GET /api/health — quick alive check."""
    return web.json_response({"ok": True, "ts": datetime.now().isoformat()})


async def me(request: web.Request) -> web.Response:
    """GET /api/me — user info + subscriptions."""
    tg_id = await _resolve_user_id(request)
    if tg_id is None:
        return web.json_response({"error": "unauthorized"}, status=401)

    async with get_session() as session:
        ur = UserRepository(session)
        user = await ur.get_by_tg_id(tg_id)
        if user is None:
            return web.json_response({"error": "user_not_found"}, status=404)

        sub_repo = SubscriptionRepository(session)
        subs = await sub_repo.list_by_user(user.id)

        return web.json_response({
            "user": {
                "id": user.id,
                "tg_id": user.tg_id,
                "full_name": user.full_name,
                "username": user.username,
                "language": user.language,
                "quiet_hours": user.quiet_hours_enabled,
                "is_admin": user.is_admin,
            },
            "subscriptions": [
                {
                    "region_id": s.region_id,
                    "region_name": s.region.name,
                    "latitude": s.region.latitude,
                    "longitude": s.region.longitude,
                    "country": s.region.country,
                    "daily_post": s.daily_post,
                    "notify_farz": s.notify_farz,
                    "notify_nafl": s.notify_nafl,
                }
                for s in subs
            ],
        })


async def times(request: web.Request) -> web.Response:
    """GET /api/times?region_id=X&date=YYYY-MM-DD — namoz vaqtlari + nafl."""
    settings = get_settings()
    try:
        region_id = int(request.query["region_id"])
    except (KeyError, ValueError):
        return web.json_response({"error": "region_id required"}, status=400)

    date_str = request.query.get("date")
    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            return web.json_response({"error": "bad date"}, status=400)
    else:
        target_date = date.today()

    async with get_session() as session:
        rr = RegionRepository(session)
        region = await rr.get(region_id)
        if region is None:
            return web.json_response({"error": "region_not_found"}, status=404)

        try:
            pt = await get_prayer_service().fetch_for_region(region, target_date)
        except ProviderError as e:
            return web.json_response(
                {"error": "provider_failed", "detail": str(e)},
                status=502,
            )

        tz = pytz.timezone(region.timezone or settings.TIMEZONE)
        nafl = calculate_nafl_windows(
            region_times=pt.times, masjid_times={},
            target_date=target_date, tz=tz,
        )
        hijriy = gregorian_to_hijri_uz(target_date)

        # Bugungi ayat
        ayah = get_daily_ayah(target_date.toordinal())

    return web.json_response({
        "region": {
            "id": region.id,
            "name": region.name,
            "country": region.country,
            "timezone": region.timezone,
            "latitude": region.latitude,
            "longitude": region.longitude,
        },
        "date": target_date.isoformat(),
        "hijri": hijriy,
        "provider": pt.provider,
        "times": pt.times,
        "nafl": nafl,
        "ayah": {
            "arabic": ayah.arabic,
            "uzbek": ayah.uzbek,
            "ref": ayah.ref,
        },
    })


async def qibla(request: web.Request) -> web.Response:
    """GET /api/qibla?lat=X&lon=Y — qibla azimut + masofa."""
    try:
        lat = float(request.query["lat"])
        lon = float(request.query["lon"])
    except (KeyError, ValueError):
        return web.json_response({"error": "lat and lon required"}, status=400)

    bearing = calculate_qibla_bearing(lat, lon)
    distance = calculate_qibla_distance_km(lat, lon)
    return web.json_response({
        "bearing": bearing,
        "distance_km": distance,
        "kaaba": {"lat": 21.4225, "lon": 39.8262},
    })


async def search_regions(request: web.Request) -> web.Response:
    """GET /api/regions/search?q=Toshkent — substring qidiruv."""
    q = request.query.get("q", "").strip()
    if len(q) < 2:
        return web.json_response({"results": []})

    async with get_session() as session:
        stmt = (
            select(Region)
            .where(
                Region.is_active.is_(True),
                Region.name.ilike(f"%{q}%"),
            )
            .order_by(Region.name)
            .limit(20)
        )
        result = await session.execute(stmt)
        regions = list(result.scalars().all())

    return web.json_response({
        "results": [
            {
                "id": r.id,
                "name": r.name,
                "country": r.country,
                "lat": r.latitude,
                "lon": r.longitude,
            }
            for r in regions
        ],
    })


def setup_api_routes(app: web.Application) -> None:
    """API routelarni `web.Application` ga ulash."""
    app.router.add_get("/api/health", health)
    app.router.add_get("/api/me", me)
    app.router.add_get("/api/times", times)
    app.router.add_get("/api/qibla", qibla)
    app.router.add_get("/api/regions/search", search_regions)


__all__ = ["setup_api_routes"]
