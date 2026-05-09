"""user'larga quiet_hours_enabled qo'shish

Revision ID: 0004_user_quiet_hours
Revises: 0003_region_geo
Create Date: 2026-05-10 00:00:00

User uchun "tinch soatlar" — agar yoqilgan bo'lsa, 23:00–05:00 (mahalliy vaqt)
oraligida farz va tahajjud DM eslatmalari yuborilmaydi.

Default: FALSE (eslatmalar har doim keladi).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_user_quiet_hours"
down_revision: str | None = "0003_region_geo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column(
                "quiet_hours_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("quiet_hours_enabled")
