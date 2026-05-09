"""SQLAlchemy bazaviy klass va metadata."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Constraint nomlari uchun naming convention
# (Alembic auto-migrasiyalar uchun MUHIM — har xil DB da bir xil nom bo'ladi)
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Loyihaning barcha ORM modellari uchun bazaviy klass."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """`created_at` va `updated_at` ustunlarini avtomatik qo'shadi."""

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )
