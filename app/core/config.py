"""Bot konfiguratsiyasi — .env fayldan o'qiladi."""
from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Loyiha ildizi
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Barcha bot sozlamalari shu yerda jamlangan."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---------------- Telegram ----------------
    BOT_TOKEN: str = Field(..., description="Telegram BotFather tokeni")
    ADMIN_IDS: str = Field(default="", description="Vergul bilan ajratilgan admin ID lar")

    # ---------------- Vaqt ----------------
    DAILY_POST_TIME: str = Field(default="06:00", description="Har kuni post vaqti (HH:MM)")
    TIMEZONE: str = Field(default="Asia/Tashkent")

    # ---------------- Database ----------------
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///data/bot.db",
        description="SQLAlchemy async DB URL",
    )

    # ---------------- Provider ----------------
    PRAYER_PROVIDER_PRIMARY: str = Field(default="islomapi")
    PRAYER_PROVIDER_FALLBACK: str = Field(default="praytime")
    ISLOMAPI_BASE_URL: str = Field(default="https://islomapi.uz")
    PRAYTIME_BASE_URL: str = Field(default="https://praytime.uz")
    PROVIDER_TIMEOUT: int = Field(default=15, ge=1, le=60)

    # ---------------- Logging ----------------
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE: str = Field(default="logs/bot.log")
    LOG_ROTATION: str = Field(default="10 MB")
    LOG_RETENTION: str = Field(default="30 days")

    # ---------------- Notification ----------------
    NOTIFY_FARZ_DEFAULT: bool = Field(default=True)
    NOTIFICATION_DELETE_AFTER: int = Field(default=300, ge=0)

    # ---------------- Mini App (Telegram WebApp) ----------------
    #: HTTPS URL — bo'sh bo'lsa WebApp tugmasi ko'rsatilmaydi.
    #: Local dev uchun: `ngrok http 8080` → https://xxx.ngrok-free.app
    WEBAPP_URL: str = Field(default="", description="Mini-app HTTPS URL")
    #: aiohttp web server porti (lokal)
    WEBAPP_PORT: int = Field(default=8080, ge=1, le=65535)

    # =================== Validators ===================

    @field_validator("DAILY_POST_TIME")
    @classmethod
    def _validate_time(cls, v: str) -> str:
        try:
            hh, mm = map(int, v.split(":"))
            assert 0 <= hh <= 23 and 0 <= mm <= 59
        except (ValueError, AssertionError) as e:
            raise ValueError(f"DAILY_POST_TIME noto'g'ri formatda: {v}. Kutilgan: HH:MM") from e
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        v = v.upper()
        if v not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"LOG_LEVEL noto'g'ri: {v}")
        return v

    # =================== Computed properties ===================

    @property
    def admin_ids_list(self) -> list[int]:
        """ADMIN_IDS string ni int listga aylantiradi."""
        if not self.ADMIN_IDS.strip():
            return []
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip()]

    @property
    def post_hour(self) -> int:
        return int(self.DAILY_POST_TIME.split(":")[0])

    @property
    def post_minute(self) -> int:
        return int(self.DAILY_POST_TIME.split(":")[1])

    @property
    def base_dir(self) -> Path:
        return BASE_DIR

    @property
    def data_dir(self) -> Path:
        d = BASE_DIR / "data"
        d.mkdir(exist_ok=True)
        return d

    @property
    def images_dir(self) -> Path:
        d = self.data_dir / "images"
        d.mkdir(exist_ok=True)
        return d

    @property
    def logs_dir(self) -> Path:
        d = BASE_DIR / "logs"
        d.mkdir(exist_ok=True)
        return d

    @property
    def static_dir(self) -> Path:
        return BASE_DIR / "static"


# Global singleton — bir marta yuklanadi
_settings: Settings | None = None


def get_settings() -> Settings:
    """Settings ni lazy yuklash (test uchun ham qulay)."""
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings
