"""Yuborilgan postlar tarixi (audit log)."""
from __future__ import annotations

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PostLog(Base):
    """
    Har bir post yoki bildirishnoma yuborishni qayd etadi.

    Maqsad: xatolarni topish, statistika, retry-mantiq.
    """

    __tablename__ = "post_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    region_id: Mapped[int | None] = mapped_column(
        ForeignKey("regions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    #: Qaysi chatga yuborildi (kanal yoki user)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    #: Telegram message_id (bo'lsa)
    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    #: Post turi: "daily" / "farz_notification" / "test" / "broadcast"
    post_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    #: Status: "ok" / "error" / "blocked"
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ok", index=True)

    #: Xato matni (status='error' bo'lsa)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    #: Yuborilgan vaqt
    posted_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<PostLog {self.id} {self.post_type}/{self.status} chat_id={self.chat_id}>"
