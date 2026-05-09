"""DB backup job — har kuni 03:00 da SQLite faylni nusxalaydi."""
from __future__ import annotations

import shutil
from datetime import date, datetime, timedelta

from app.core.config import get_settings
from app.core.logger import logger

#: Necha kunlik backup saqlanadi (eskilari avtomatik o'chiriladi)
RETENTION_DAYS = 30


async def run_db_backup() -> None:
    """SQLite DB faylni `backups/bot_YYYYMMDD.db` ga nusxalash + rotatsiya."""
    settings = get_settings()
    db_url = settings.DATABASE_URL

    if not db_url.startswith("sqlite"):
        logger.warning(
            "Backup faqat SQLite uchun. Joriy DATABASE_URL: {}", db_url,
        )
        return

    # `sqlite+aiosqlite:///data/bot.db` → `data/bot.db`
    rel_path = db_url.split("///", 1)[-1] if "///" in db_url else db_url
    db_path = settings.base_dir / rel_path

    if not db_path.exists():
        logger.warning("DB fayl topilmadi: {}", db_path)
        return

    backup_dir = settings.base_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    today_str = date.today().strftime("%Y%m%d")
    backup_path = backup_dir / f"bot_{today_str}.db"

    try:
        shutil.copy2(db_path, backup_path)
    except OSError as e:
        logger.error("DB backup nusxa olinmadi: {}", e)
        return

    size_kb = backup_path.stat().st_size // 1024
    logger.info("📦 DB backup yaratildi: {} ({} KB)", backup_path.name, size_kb)

    # Rotatsiya — `RETENTION_DAYS` dan eskilari o'chiriladi
    cutoff = date.today() - timedelta(days=RETENTION_DAYS)
    removed = 0
    for f in backup_dir.glob("bot_*.db"):
        try:
            d_str = f.stem.split("_", 1)[1]
            f_date = datetime.strptime(d_str, "%Y%m%d").date()
        except (ValueError, IndexError):
            continue
        if f_date < cutoff:
            try:
                f.unlink()
                removed += 1
            except OSError as e:
                logger.warning("Eski backup o'chmadi {}: {}", f.name, e)
    if removed:
        logger.info("Eski backuplar o'chirildi: {} ta", removed)


__all__ = ["run_db_backup"]
