"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-08 00:00:00

Birinchi migrasiya — barcha jadvallarni yaratadi.

Jadvallar:
- regions          (viloyat/tuman ierarxiyasi)
- channels         (Telegram kanallar)
- users            (DM obunachilar)
- subscriptions    (User <-> Region)
- masjid_times     (jamoat vaqtlari)
- post_logs        (yuborilgan postlar)
- stat_events      (statistika)
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ============== regions ==============
    op.create_table(
        "regions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("provider_name", sa.String(length=64), nullable=True),
        sa.Column("praytime_id", sa.Integer(), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("timezone", sa.String(length=64), server_default="Asia/Tashkent", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["regions.id"], name=op.f("fk_regions_parent_id_regions"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_regions")),
        sa.UniqueConstraint("name", name=op.f("uq_regions_name")),
        sa.UniqueConstraint("slug", name=op.f("uq_regions_slug")),
    )

    # ============== channels ==============
    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("link", sa.String(length=256), nullable=True),
        sa.Column("title", sa.String(length=256), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("custom_caption_template", sa.String(length=4096), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"], name=op.f("fk_channels_region_id_regions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_channels")),
        sa.UniqueConstraint("chat_id", name=op.f("uq_channels_chat_id")),
    )
    op.create_index(op.f("ix_channels_region_id"), "channels", ["region_id"])

    # ============== users ==============
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tg_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("full_name", sa.String(length=256), nullable=True),
        sa.Column("language", sa.String(length=8), server_default="uz", nullable=False),
        sa.Column("is_blocked", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("tg_id", name=op.f("uq_users_tg_id")),
    )
    op.create_index(op.f("ix_users_tg_id"), "users", ["tg_id"])

    # ============== subscriptions ==============
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("region_id", sa.Integer(), nullable=False),
        sa.Column("daily_post", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("notify_farz", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("notify_nafl", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"], name=op.f("fk_subscriptions_region_id_regions"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_subscriptions_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subscriptions")),
        sa.UniqueConstraint("user_id", "region_id", name="user_region"),
    )
    op.create_index(op.f("ix_subscriptions_user_id"), "subscriptions", ["user_id"])
    op.create_index(op.f("ix_subscriptions_region_id"), "subscriptions", ["region_id"])

    # ============== masjid_times ==============
    op.create_table(
        "masjid_times",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_id", sa.Integer(), nullable=False),
        sa.Column("prayer", sa.String(length=16), nullable=False),
        sa.Column("time", sa.String(length=5), nullable=False),
        sa.Column("updated_by_tg_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"], name=op.f("fk_masjid_times_region_id_regions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_masjid_times")),
        sa.UniqueConstraint("region_id", "prayer", name="region_prayer"),
    )
    op.create_index(op.f("ix_masjid_times_region_id"), "masjid_times", ["region_id"])

    # ============== post_logs ==============
    op.create_table(
        "post_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_id", sa.Integer(), nullable=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("post_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="ok", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"], name=op.f("fk_post_logs_region_id_regions"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_post_logs")),
    )
    op.create_index(op.f("ix_post_logs_region_id"), "post_logs", ["region_id"])
    op.create_index(op.f("ix_post_logs_chat_id"), "post_logs", ["chat_id"])
    op.create_index(op.f("ix_post_logs_post_type"), "post_logs", ["post_type"])
    op.create_index(op.f("ix_post_logs_status"), "post_logs", ["status"])
    op.create_index(op.f("ix_post_logs_posted_at"), "post_logs", ["posted_at"])

    # ============== stat_events ==============
    op.create_table(
        "stat_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("region_id", sa.Integer(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"], name=op.f("fk_stat_events_region_id_regions"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_stat_events_user_id_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stat_events")),
    )
    op.create_index(op.f("ix_stat_events_event"), "stat_events", ["event"])
    op.create_index(op.f("ix_stat_events_user_id"), "stat_events", ["user_id"])
    op.create_index(op.f("ix_stat_events_region_id"), "stat_events", ["region_id"])
    op.create_index(op.f("ix_stat_events_created_at"), "stat_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("stat_events")
    op.drop_table("post_logs")
    op.drop_table("masjid_times")
    op.drop_table("subscriptions")
    op.drop_table("users")
    op.drop_table("channels")
    op.drop_table("regions")
