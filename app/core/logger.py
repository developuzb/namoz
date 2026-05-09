"""Loglash — loguru orqali strukturali, fayl rotatsiyali."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from loguru import logger

from app.core.config import get_settings


class _InterceptHandler(logging.Handler):
    """Python `logging` xabarlarini loguru ga yo'naltiradi (aiogram, sqlalchemy uchun)."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logger() -> None:
    """Loguru ni sozlash. Bot ishga tushganda bir marta chaqiriladi."""
    settings = get_settings()

    # Default handler ni o'chiramiz
    logger.remove()

    # ==== Konsolga chiqarish (ranglar bilan) ====
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,
        backtrace=True,
        diagnose=settings.LOG_LEVEL == "DEBUG",
    )

    # ==== Faylga yozish (rotatsiyali) ====
    log_path = Path(settings.LOG_FILE)
    if not log_path.is_absolute():
        log_path = settings.base_dir / log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_path,
        level=settings.LOG_LEVEL,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} - {message}"
        ),
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression="zip",
        encoding="utf-8",
        backtrace=True,
        diagnose=False,
        enqueue=True,  # async-safe
    )

    # ==== Xatolar uchun alohida fayl ====
    err_path = log_path.parent / "errors.log"
    logger.add(
        err_path,
        level="ERROR",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} - {message}\n{exception}"
        ),
        rotation="10 MB",
        retention="60 days",
        compression="zip",
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )

    # Python `logging` modulini loguru ga ulash (aiogram, sqlalchemy va h.k.)
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    for noisy in ("aiogram.event", "aiogram.dispatcher"):
        logging.getLogger(noisy).setLevel(logging.INFO)

    logger.info(
        "📝 Logger sozlandi (level={}, file={})",
        settings.LOG_LEVEL,
        log_path,
    )


# Re-export — boshqa joydan `from app.core.logger import logger`
__all__ = ["logger", "setup_logger"]
