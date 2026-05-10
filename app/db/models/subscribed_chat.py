"""Guruh chatlar uchun obuna modeli (DM emas — guruh / supergruh)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.region import Region


class SubscribedChat(Base, TimestampMixin):
    """
    Guruh yoki supergruh chati hudud uchun obuna bo'lgan.

    DM obunalari `subscriptions` jadvalida — bu yer faqat guruhlar uchun.
    """

    __tablename__ = "subscribed_chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    #: Telegram chat_id (guruhlar uchun manfiy)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)

    #: Guruh nomi (admin ko'rishi uchun)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)

    #: "group" / "supergroup" / "channel"
    chat_type: Mapped[str] = mapped_column(String(32), nullable=False)

    region_id: Mapped[int] = mapped_column(
        ForeignKey("regions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    #: Kunlik post yuborilsinmi
    daily_post: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    #: Farz vaqtida eslatma yuborilsinmi (default OFF — guruhda spam bo'lmasin)
    notify_farz: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    #: Kim obuna qilgan (admin tg_id)
    added_by_tg_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    region: Mapped[Region] = relationship("Region")

    def __repr__(self) -> str:
        return (
            f"<SubscribedChat {self.id} chat_id={self.chat_id} "
            f"region_id={self.region_id}>"
        )
