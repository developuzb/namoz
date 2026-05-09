"""seed: Qashqadaryo viloyati va tumanlari

Revision ID: 0002_seed_qashqadaryo
Revises: 0001_initial
Create Date: 2026-05-08 00:00:01

Eski botdagi 14 tumanni DB ga yozadi (Channel siz, faqat Region).
Adminlar keyin bot ichidan kanal qo'shadi.

Note: Ko'kdala uchun praytime_id eski kodda Shahrisabz bilan bir xil edi (134) —
to'g'ri ID topilguncha shu ko'rinishda qoldirildi (kerak bo'lsa keyin yangilash mumkin).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "0002_seed_qashqadaryo"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (name, slug, provider_name, praytime_id)
_DISTRICTS: list[tuple[str, str, str, int]] = [
    ("Qarshi",      "qarshi",      "Qarshi",      121),
    ("Dehqonobod",  "dehqonobod",  "Dehqonobod",  124),
    ("G‘uzor",      "guzor",       "G‘uzor",      123),
    ("Kasbi",       "kasbi",       "Kasbi",       130),
    ("Kitob",       "kitob",       "Kitob",       134),
    ("Koson",       "koson",       "Koson",       126),
    ("Mirishkor",   "mirishkor",   "Mirishkor",   128),
    ("Muborak",     "muborak",     "Muborak",     127),
    ("Nishon",      "nishon",      "Nishon",      122),
    ("Qamashi",     "qamashi",     "Qamashi",     125),
    ("Shahrisabz",  "shahrisabz",  "Shahrisabz",  133),
    ("Yakkabog‘",   "yakkabog",    "Yakkabog‘",   132),
    ("Chiroqchi",   "chiroqchi",   "Chiroqchi",   131),
    ("Ko‘kdala",    "kokdala",     "Ko‘kdala",    134),  # Shahrisabz ID si bilan bir xil
]

_DEFAULT_MASJID_TIMES = {
    "Bomdod": "07:00",
    "Peshin": "13:00",
    "Asr":    "16:20",
    "Shom":   "18:05",
    "Xufton": "19:35",
}


def upgrade() -> None:
    bind = op.get_bind()

    regions_table = sa.table(
        "regions",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("provider_name", sa.String),
        sa.column("praytime_id", sa.Integer),
        sa.column("parent_id", sa.Integer),
        sa.column("timezone", sa.String),
        sa.column("is_active", sa.Boolean),
    )

    # 1) Qashqadaryo viloyati (parent)
    bind.execute(
        sa.insert(regions_table).values(
            name="Qashqadaryo viloyati",
            slug="qashqadaryo",
            provider_name=None,
            praytime_id=None,
            parent_id=None,
            timezone="Asia/Tashkent",
            is_active=True,
        )
    )

    parent_id = bind.execute(
        sa.select(regions_table.c.id).where(regions_table.c.slug == "qashqadaryo")
    ).scalar_one()

    # 2) Tumanlar
    bind.execute(
        sa.insert(regions_table),
        [
            {
                "name": name,
                "slug": slug,
                "provider_name": provider_name,
                "praytime_id": praytime_id,
                "parent_id": parent_id,
                "timezone": "Asia/Tashkent",
                "is_active": True,
            }
            for name, slug, provider_name, praytime_id in _DISTRICTS
        ],
    )

    # 3) Default masjid vaqtlari (har tuman uchun bir xil)
    masjid_table = sa.table(
        "masjid_times",
        sa.column("region_id", sa.Integer),
        sa.column("prayer", sa.String),
        sa.column("time", sa.String),
        sa.column("updated_by_tg_id", sa.BigInteger),
    )

    district_ids = bind.execute(
        sa.select(regions_table.c.id).where(regions_table.c.parent_id == parent_id)
    ).scalars().all()

    rows = []
    for region_id in district_ids:
        for prayer, time in _DEFAULT_MASJID_TIMES.items():
            rows.append(
                {
                    "region_id": region_id,
                    "prayer": prayer,
                    "time": time,
                    "updated_by_tg_id": None,
                }
            )

    if rows:
        bind.execute(sa.insert(masjid_table), rows)


def downgrade() -> None:
    bind = op.get_bind()
    # Tumanlar va viloyatni tozalash (CASCADE bilan masjid_times ham tushadi)
    bind.execute(sa.text("DELETE FROM regions WHERE slug = 'qashqadaryo' OR parent_id IN (SELECT id FROM regions WHERE slug = 'qashqadaryo')"))
