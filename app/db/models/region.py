"""Hudud (viloyat / tuman) modeli."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.channel import Channel
    from app.db.models.masjid_time import MasjidTime
    from app.db.models.subscription import Subscription


class Region(Base, TimestampMixin):
    """
    Hudud — viloyat yoki tuman.

    `parent_id` bilan ierarxiya: viloyat -> tumanlar.
    `provider_id` — provider (islomapi/praytime) da hududning ID si.
    """

    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    #: Foydalanuvchi ko'radigan nom (masalan, "Qarshi", "Shahrisabz")
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    #: URL-friendly ko'rinish (masalan, "qarshi") — slash, callback_data uchun
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    #: Provider da bu hudud qanday ataladi (masalan, "Qarshi")
    #: Agar slug == provider_name bo'lsa, NULL bo'lishi mumkin
    provider_name: Mapped[str | None] = mapped_column(String(64), nullable=True)

    #: praytime.uz uchun raqamli ID (zaxira)
    praytime_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    #: Ota-hudud (viloyat). Tuman bo'lsa to'ldiriladi.
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("regions.id", ondelete="SET NULL"),
        nullable=True,
    )

    #: Vaqt zonasi (default Asia/Tashkent)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Tashkent", nullable=False)

    #: Markaz koordinatalari (lokatsiya orqali yaratilgan regionlar uchun MAJBURIY)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    #: Aladhan API uchun hisoblash usuli (default 2 = ISNA)
    #: https://aladhan.com/calculation-methods
    aladhan_method: Mapped[int] = mapped_column(SmallInteger, default=2, nullable=False)

    #: Aladhan Asr maktabi: 0 = Shafi/Maliki/Hanbali, 1 = Hanafi (default)
    aladhan_school: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)

    #: Mamlakat (lokatsiya orqali yaratilgan regionlar uchun)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)

    #: Faol / faolsiz
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ---------------- Relationships ----------------

    parent: Mapped[Region | None] = relationship(
        "Region",
        remote_side="Region.id",
        back_populates="children",
    )
    children: Mapped[list[Region]] = relationship(
        "Region",
        back_populates="parent",
        cascade="all",
    )

    channels: Mapped[list[Channel]] = relationship(
        "Channel",
        back_populates="region",
        cascade="all, delete-orphan",
    )
    masjid_times: Mapped[list[MasjidTime]] = relationship(
        "MasjidTime",
        back_populates="region",
        cascade="all, delete-orphan",
    )
    subscriptions: Mapped[list[Subscription]] = relationship(
        "Subscription",
        back_populates="region",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Region {self.id} {self.name!r}>"
