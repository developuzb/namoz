"""End-to-end test: DB dan 14 tuman uchun haqiqiy vaqtlar olib, plakat yasaydi.

Ishga tushirish:
    python -m scripts.test_qashqadaryo_pipeline
"""
from __future__ import annotations

import asyncio
from datetime import date

from app.scheduler.jobs.qashqadaryo_post import build_qashqadaryo_image


async def main() -> None:
    path, regions_data = await build_qashqadaryo_image(
        target_date=date.today(), test_mode=True,
    )
    print(f"\nSaved: {path}")
    print(f"Tumans with times: {len(regions_data)}")
    for name, times in regions_data.items():
        keys = ",".join(times.keys())
        print(f"  {name}: {keys}")


if __name__ == "__main__":
    asyncio.run(main())
