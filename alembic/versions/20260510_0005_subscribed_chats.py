"""subscribed_chats jadval — guruh chatlar uchun obuna

Revision ID: 0005_subscribed_chats
Revises: 0004_user_quiet_hours
Create Date: 2026-05-10 02:00:00

Bot guruh chatga qo'shilgach, admin /subscribe Qarshi bilan guruhni
hududga obuna qiladi. Kunlik post guruhga ham boradi.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_subscribed_chats"
down_revision: str | None = "0004_user_quiet_hours"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "subscribed_chats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=True),
        sa.Column("chat_type", sa.String(length=32), nullable=False),
        sa.Column("region_id", sa.Integer(), nullable=False),
        sa.Column(
            "daily_post", sa.Boolean(), server_default=sa.true(), nullable=False,
        ),
        sa.Column(
            "notify_farz", sa.Boolean(), server_default=sa.false(), nullable=False,
        ),
        sa.Column("added_by_tg_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.true(), nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(),
            server_default=sa.func.current_timestamp(), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(),
            server_default=sa.func.current_timestamp(), nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["region_id"], ["regions.id"],
            name=op.f("fk_subscribed_chats_region_id_regions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subscribed_chats")),
        sa.UniqueConstraint("chat_id", name=op.f("uq_subscribed_chats_chat_id")),
    )
    op.create_index(
        op.f("ix_subscribed_chats_region_id"),
        "subscribed_chats", ["region_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_subscribed_chats_region_id"), table_name="subscribed_chats",
    )
    op.drop_table("subscribed_chats")
