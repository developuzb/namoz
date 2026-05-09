"""Bot foydalanuvchisi modeli (DM obunachilar)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.subscription import Subscription


class User(Base, TimestampMixin):
    """
    Bot bilan DM da yozishgan foydalanuvchi.

    Birinchi `/start` paytida avtomatik yaratiladi (user_register middleware).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    #: Telegram user ID (UNIQUE)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)

    #: @username (bo'lsa)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)

    #: Familiya + ism
    full_name: Mapped[str | None] = mapped_column(String(256), nullable=True)

    #: Til kodi (default 'uz')
    language: Mapped[str] = mapped_column(String(8), default="uz", nullable=False)

    #: Bot bloklanganmi (ForbiddenError tushganda True ga o'tadi)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    #: Admin huquqi (ADMIN_IDS dan tashqari ham qo'shilishi mumkin)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    #: Tinch soatlar (23:00–05:00 mahalliy) — yoqilgan bo'lsa, kechqurun
    #: farz/tahajjud eslatmalari yuborilmaydi
    quiet_hours_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # ---------------- Relationships ----------------

    subscriptions: Mapped[list[Subscription]] = relationship(
        "Subscription",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User {self.id} tg_id={self.tg_id} {self.username!r}>"
