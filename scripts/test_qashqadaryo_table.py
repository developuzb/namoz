"""Visual smoke-test — Qashqadaryo plakatining test rasmini yasaydi.

Ishga tushirish:
    python -m scripts.test_qashqadaryo_table
"""
from __future__ import annotations

from datetime import date

from app.services.qashqadaryo_table import TUMAN_ORDER_CYR, render_qashqadaryo_table


def _fake_times(seed: int) -> dict[str, str]:
    """Har tuman uchun biroz boshqacharoq, ammo realistik vaqtlar."""
    base = {
        "Bomdod": (4, 14),
        "Quyosh": (5, 39),
        "Peshin": (12, 34),
        "Asr":    (17, 27),
        "Shom":   (19, 32),
        "Xufton": (20, 54),
    }
    out = {}
    for k, (h, m) in base.items():
        m2 = (m + seed) % 60
        out[k] = f"{h:02d}:{m2:02d}"
    return out


def main() -> None:
    regions_data = {
        lotin: _fake_times(i * 3) for i, (lotin, _) in enumerate(TUMAN_ORDER_CYR)
    }

    masjid = {
        "Bomdod": "05:00",
        "Peshin": "13:00",
        "Asr":    "17:45",
        "Shom":   "19:35",
        "Xufton": "21:10",
    }

    out = render_qashqadaryo_table(
        target_date=date(2026, 5, 12),
        regions_data=regions_data,
        masjid_times=masjid,
        test_mode=True,
    )
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
