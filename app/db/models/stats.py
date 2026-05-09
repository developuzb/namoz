"""Foydalanuvchi statistikasi (event log)."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column


from app.db.base import Base


class StatEvent(Base):
    """
    Statistika eventi — har bir muhim foydalanuvchi harakati.

    Eventlar:
      - "start"            — /start bosildi
      - "subscribe"        — hududga obuna bo'ldi
      - "unsubscribe"      — obunani bekor qildi
      - "click_next_farz"  — "Keyingi farz" tugmasi bosildi
      - "click_nafl_info"  — "Hozir qaysi nafl?" tugmasi bosildi
      - "settings_changed" — sozlamasi o'zgardi

    Maqsad: kelajakda dashboard chizish va aktivlikni o'lchash.
    """

    __tablename__ = "stat_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    #: Event nomi
    event: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    #: Foydalanuvchi (NULL — anonim/system event uchun)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    #: Hudud (agar tegishli bo'lsa)
    region_id: Mapped[int | None] = mapped_column(
        ForeignKey("regions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    #: Qo'shimcha ma'lumot (JSON)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<StatEvent {self.id} {self.event!r} user_id={self.user_id}>"
