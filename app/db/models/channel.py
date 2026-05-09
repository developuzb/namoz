"""Telegram kanal modeli."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.region import Region


class Channel(Base, TimestampMixin):
    """
    Hudud uchun Telegram kanal.

    Bir hududga bir nechta kanal biriktirish mumkin.
    """

    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    region_id: Mapped[int] = mapped_column(
        ForeignKey("regions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    #: Telegram chat_id (kanallar uchun manfiy son, masalan -1003051640118)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)

    #: Ko'rinadigan havola: "@qarshi_masjidi" yoki "https://t.me/..."
    link: Mapped[str | None] = mapped_column(String(256), nullable=True)

    #: Kanal nomi (admin ko'rishi uchun)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)

    #: Kanalga post yuborilsinmi
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    #: Caption shabloni (maxsus matn). NULL bo'lsa default ishlatiladi.
    custom_caption_template: Mapped[str | None] = mapped_column(String(4096), nullable=True)

    # ---------------- Relationships ----------------

    region: Mapped[Region] = relationship("Region", back_populates="channels")

    def __repr__(self) -> str:
        return f"<Channel {self.id} chat_id={self.chat_id} region_id={self.region_id}>"
