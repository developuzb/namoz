"""Foydalanuvchi obunasi: User ↔ Region."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.region import Region
    from app.db.models.user import User


class Subscription(Base, TimestampMixin):
    """
    Foydalanuvchi qaysi hududga obuna bo'lganini saqlaydi.

    Bir user bir nechta hududga obuna bo'lishi mumkin (chegara: MAX_SUBSCRIPTIONS_PER_USER).
    """

    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "region_id", name="user_region"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    region_id: Mapped[int] = mapped_column(
        ForeignKey("regions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    #: Kunlik post DM ga yuborilsinmi
    daily_post: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    #: Farz vaqtida bildirishnoma DM ga yuborilsinmi
    notify_farz: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    #: Nafl haqida eslatma yuborilsinmi
    notify_nafl: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ---------------- Relationships ----------------

    user: Mapped[User] = relationship("User", back_populates="subscriptions")
    region: Mapped[Region] = relationship("Region", back_populates="subscriptions")

    def __repr__(self) -> str:
        return f"<Subscription user_id={self.user_id} region_id={self.region_id}>"
