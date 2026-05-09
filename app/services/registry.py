"""Singleton service instance'lari — cache handler va scheduler o'rtasida shared."""
from __future__ import annotations

from app.services.post_service import PostService
from app.services.prayer_provider import PrayerService

_prayer_service: PrayerService | None = None
_post_service: PostService | None = None


def get_prayer_service() -> PrayerService:
    """Lazy singleton — birinchi chaqiriqda yaratadi."""
    global _prayer_service
    if _prayer_service is None:
        _prayer_service = PrayerService()
    return _prayer_service


def get_post_service() -> PostService:
    global _post_service
    if _post_service is None:
        _post_service = PostService(prayer_service=get_prayer_service())
    return _post_service


__all__ = ["get_post_service", "get_prayer_service"]
