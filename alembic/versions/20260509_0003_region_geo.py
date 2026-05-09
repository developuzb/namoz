"""regions ga lat/lon/aladhan ustunlari

Revision ID: 0003_region_geo
Revises: 0002_seed_qashqadaryo
Create Date: 2026-05-09 00:00:00

Yer yuzining istalgan joyida ishlash uchun:
- latitude/longitude — Aladhan API ga uzatish + masofa hisoblash uchun
- aladhan_method — hisoblash usuli (default 2 = ISNA)
- aladhan_school — Asr maktabi (default 1 = Hanafi)
- country — mamlakat nomi (Nominatim dan keladi)

Mavjud Qashqadaryo regionlariga ham koordinatalar to'ldiramiz —
"eng yaqin hudud" qidiruvi ham ularni topadi.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_region_geo"
down_revision: str | None = "0002_seed_qashqadaryo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Qashqadaryo tumanlari va viloyatining markaz koordinatalari (Wikipedia/Maps)
_CENTROIDS: list[tuple[str, float, float]] = [
    ("qashqadaryo", 38.8650, 65.7920),  # viloyat markazi (Qarshi yaqinida)
    ("qarshi",      38.8650, 65.7920),
    ("dehqonobod",  38.3286, 66.6650),
    ("guzor",       38.6133, 66.2461),
    ("kasbi",       38.7861, 65.6539),
    ("kitob",       39.1267, 66.8767),
    ("koson",       39.0386, 65.5944),
    ("mirishkor",   38.9333, 65.1167),
    ("muborak",     39.2497, 65.1497),
    ("nishon",      38.5103, 65.7892),
    ("qamashi",     38.8092, 66.4439),
    ("shahrisabz",  39.0581, 66.8281),
    ("yakkabog",    38.9656, 66.6692),
    ("chiroqchi",   39.0361, 66.5781),
    ("kokdala",     39.0581, 66.8281),  # Shahrisabz yaqin
]


def upgrade() -> None:
    with op.batch_alter_table("regions") as batch:
        batch.add_column(sa.Column("latitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("longitude", sa.Float(), nullable=True))
        batch.add_column(
            sa.Column(
                "aladhan_method",
                sa.SmallInteger(),
                nullable=False,
                server_default="2",
            )
        )
        batch.add_column(
            sa.Column(
                "aladhan_school",
                sa.SmallInteger(),
                nullable=False,
                server_default="1",
            )
        )
        batch.add_column(sa.Column("country", sa.String(length=64), nullable=True))

    # Mavjud Qashqadaryo regionlariga koordinata to'ldirish
    bind = op.get_bind()
    for slug, lat, lon in _CENTROIDS:
        bind.execute(
            sa.text(
                "UPDATE regions SET latitude = :lat, longitude = :lon, country = :ctry "
                "WHERE slug = :slug"
            ),
            {"lat": lat, "lon": lon, "ctry": "Oʻzbekiston", "slug": slug},
        )


def downgrade() -> None:
    with op.batch_alter_table("regions") as batch:
        batch.drop_column("country")
        batch.drop_column("aladhan_school")
        batch.drop_column("aladhan_method")
        batch.drop_column("longitude")
        batch.drop_column("latitude")
