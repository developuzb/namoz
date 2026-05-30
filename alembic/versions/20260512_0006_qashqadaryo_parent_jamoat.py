"""Qashqadaryo viloyati (parent) uchun bitta jamoat vaqtlari to'plami.

Avval har bir tuman uchun alohida `masjid_times` yozuvlari bor edi
(20260508_0002_seed_qashqadaryo.py). Endi:
  * Viloyat parent (slug='qashqadaryo') uchun bitta to'plam yoziladi
  * 14 tumanning eski yozuvlari o'chiriladi
  * Yangi plakat va per-tuman post pipeline'lari ikkalasi ham parent dan o'qiydi

Revision ID: 0006_qashqadaryo_parent_jamoat
Revises: 0005_subscribed_chats
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "0006_qashqadaryo_parent_jamoat"
down_revision: str | None = "0005_subscribed_chats"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_DEFAULT_JAMOAT = {
    "Bomdod": "07:00",
    "Peshin": "13:00",
    "Asr":    "16:20",
    "Shom":   "18:05",
    "Xufton": "19:35",
}


def upgrade() -> None:
    bind = op.get_bind()

    # Parent region ID ni topamiz
    row = bind.execute(
        sa.text("SELECT id FROM regions WHERE slug = 'qashqadaryo'")
    ).first()
    if row is None:
        # Seed migratsiyasi qo'llanmagan — hech narsa qilmaymiz
        return
    parent_id = row[0]

    # Tumanlar ID lari
    tuman_ids = [
        r[0] for r in bind.execute(
            sa.text("SELECT id FROM regions WHERE parent_id = :p"),
            {"p": parent_id},
        ).all()
    ]

    # 1) Tumanlar masjid_times yozuvlarini o'chirish
    if tuman_ids:
        bind.execute(
            sa.text(
                "DELETE FROM masjid_times WHERE region_id IN ("
                + ",".join(str(i) for i in tuman_ids)
                + ")"
            )
        )

    # 2) Parent uchun yangi yozuvlar (bo'lmasa)
    for prayer, time in _DEFAULT_JAMOAT.items():
        exists = bind.execute(
            sa.text(
                "SELECT 1 FROM masjid_times "
                "WHERE region_id = :r AND prayer = :p"
            ),
            {"r": parent_id, "p": prayer},
        ).first()
        if exists is None:
            bind.execute(
                sa.text(
                    "INSERT INTO masjid_times (region_id, prayer, time) "
                    "VALUES (:r, :p, :t)"
                ),
                {"r": parent_id, "p": prayer, "t": time},
            )


def downgrade() -> None:
    bind = op.get_bind()
    row = bind.execute(
        sa.text("SELECT id FROM regions WHERE slug = 'qashqadaryo'")
    ).first()
    if row is None:
        return
    parent_id = row[0]

    # Parent yozuvlarini o'chirish
    bind.execute(
        sa.text("DELETE FROM masjid_times WHERE region_id = :r"),
        {"r": parent_id},
    )

    # Tumanlar uchun default qaytarish (o'tgan migrationdagi qiymatlar)
    tuman_ids = [
        r[0] for r in bind.execute(
            sa.text("SELECT id FROM regions WHERE parent_id = :p"),
            {"p": parent_id},
        ).all()
    ]
    for tid in tuman_ids:
        for prayer, time in _DEFAULT_JAMOAT.items():
            bind.execute(
                sa.text(
                    "INSERT INTO masjid_times (region_id, prayer, time) "
                    "VALUES (:r, :p, :t)"
                ),
                {"r": tid, "p": prayer, "t": time},
            )
