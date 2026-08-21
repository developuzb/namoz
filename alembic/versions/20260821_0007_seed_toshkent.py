"""seed: Toshkent shahri va 12 tumani

Toshkent shahri — bitta namoz-vaqt zonasi (butun shahar bo'yicha vaqtlar
bir xil). 12 tuman asosan brendlash/kanal uchun alohida region qilinadi;
vaqtlari bir xil bo'ladi.

Ma'lumot manbai (provider chain):
  - islomapi provider_name="Toshkent" (rasmiy, ishlaganда)
  - aladhan latitude/longitude (ishonchli zaxira — dunyo bo'yicha)

Revision ID: 0007_seed_toshkent
Revises: 0006_qashqadaryo_parent_jamoat
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0007_seed_toshkent"
down_revision: str | None = "0006_qashqadaryo_parent_jamoat"
branch_labels = None
depends_on = None

PARENT_SLUG = "toshkent-shahri"
PROVIDER = "Toshkent"  # islomapi shahar nomi (barcha tumanlar uchun bir xil)

# (name, slug, latitude, longitude) — tuman markazlari (aladhan zaxira uchun)
_DISTRICTS: list[tuple[str, str, float, float]] = [
    ("Bektemir",       "bektemir",       41.2064, 69.3336),
    ("Chilonzor",      "chilonzor",      41.2725, 69.2044),
    ("Mirobod",        "mirobod",        41.2789, 69.2600),
    ("Mirzo Ulug'bek", "mirzo-ulugbek",  41.3275, 69.3417),
    ("Olmazor",        "olmazor",        41.3606, 69.2036),
    ("Sergeli",        "sergeli",        41.2231, 69.2231),
    ("Shayxontohur",   "shayxontohur",   41.3253, 69.2361),
    ("Uchtepa",        "uchtepa",        41.2872, 69.1739),
    ("Yakkasaroy",     "yakkasaroy",     41.2836, 69.2669),
    ("Yashnobod",      "yashnobod",      41.2917, 69.3333),
    ("Yunusobod",      "yunusobod",      41.3667, 69.2894),
    ("Yangihayot",     "yangihayot",     41.2000, 69.2500),
]


def _regions_table() -> sa.Table:
    return sa.table(
        "regions",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("provider_name", sa.String),
        sa.column("praytime_id", sa.Integer),
        sa.column("parent_id", sa.Integer),
        sa.column("timezone", sa.String),
        sa.column("latitude", sa.Float),
        sa.column("longitude", sa.Float),
        sa.column("country", sa.String),
        sa.column("is_active", sa.Boolean),
    )


def upgrade() -> None:
    bind = op.get_bind()
    regions = _regions_table()

    # 1) Toshkent shahri (parent — guruhlash, o'zi post uchun ishlatilmaydi)
    bind.execute(
        sa.insert(regions).values(
            name="Toshkent shahri",
            slug=PARENT_SLUG,
            provider_name=None,
            praytime_id=None,
            parent_id=None,
            timezone="Asia/Tashkent",
            country="Uzbekistan",
            is_active=True,
        )
    )
    parent_id = bind.execute(
        sa.select(regions.c.id).where(regions.c.slug == PARENT_SLUG)
    ).scalar_one()

    # 2) 12 tuman — hammasi Toshkent shahri vaqtlarini oladi (islomapi + aladhan)
    bind.execute(
        sa.insert(regions),
        [
            {
                "name": name,
                "slug": slug,
                "provider_name": PROVIDER,
                "praytime_id": None,
                "parent_id": parent_id,
                "timezone": "Asia/Tashkent",
                "latitude": lat,
                "longitude": lon,
                "country": "Uzbekistan",
                "is_active": True,
            }
            for name, slug, lat, lon in _DISTRICTS
        ],
    )


def downgrade() -> None:
    bind = op.get_bind()
    regions = _regions_table()

    district_slugs = [s for _, s, _, _ in _DISTRICTS]
    bind.execute(
        sa.delete(regions).where(regions.c.slug.in_(district_slugs))
    )
    bind.execute(
        sa.delete(regions).where(regions.c.slug == PARENT_SLUG)
    )
