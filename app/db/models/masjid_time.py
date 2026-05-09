"""Masjid (jamoat) namoz vaqtlari — har hudud uchun alohida."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.region import Region


class MasjidTime(Base, TimestampMixin):
    """
    Masjid jamoat vaqti — har hudud × har namoz uchun alohida yozuv.

    Eski botda JSON da edi, endi DB da. Admin har bir hudud uchun
    o'zgartirishi mumkin.
    """

    __tablename__ = "masjid_times"
    __table_args__ = (
        UniqueConstraint("region_id", "prayer", name="region_prayer"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    region_id: Mapped[int] = mapped_column(
        ForeignKey("regions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    #: Namoz nomi: Bomdod / Peshin / Asr / Shom / Xufton
    prayer: Mapped[str] = mapped_column(String(16), nullable=False)

    #: Vaqt "HH:MM" formatida (TIME emas — soddaroq, validator bor)
    time: Mapped[str] = mapped_column(String(5), nullable=False)

    #: Kim o'zgartirgan (admin tg_id)
    updated_by_tg_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # ---------------- Relationships ----------------

    region: Mapped[Region] = relationship("Region", back_populates="masjid_times")

    def __repr__(self) -> str:
        return f"<MasjidTime region_id={self.region_id} {self.prayer}={self.time}>"
