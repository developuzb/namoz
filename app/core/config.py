"""Bot konfiguratsiyasi — .env fayldan o'qiladi."""
from __future__ import annotations

import os
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
    #: False → faqat PRIMARY manba ishlatiladi (zaxira praytime/aladhan
    #: o'chiriladi). Primary tushsa — post o'tkazib yuboriladi.
    PRAYER_PROVIDER_FALLBACK_ENABLED: bool = Field(default=True)
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
    #: aiohttp web server porti (lokal). Heroku'da `$PORT` ustuvor (web_port).
    WEBAPP_PORT: int = Field(default=8080, ge=1, le=65535)
    #: CORS ruxsat etilgan originlar (vergul bilan). Frontend GitHub Pages'da
    #: bo'lgani uchun kerak. "*" — barchasiga ruxsat (initData HMAC baribir
    #: himoya qiladi). Masalan: "https://developuzb.github.io"
    WEBAPP_CORS_ORIGINS: str = Field(default="*")

    # ---------------- Qashqadaryo kunlik plakat ----------------
    #: Plakat avtomatik yuboriladigan chat (kanal/guruh) ID.
    #: 0 — o'chiq (scheduler yubormaydi, faqat /test_namoz ishlaydi).
    NAMOZ_CHAT_ID: int = Field(default=0, description="Qashqadaryo plakat chat ID")
    #: Plakat yuborish vaqti (HH:MM)
    NAMOZ_SEND_TIME: str = Field(default="04:00")
    #: Plakat uchun timezone (default — TIMEZONE ga teng)
    NAMOZ_TIMEZONE: str = Field(default="Asia/Tashkent")

    # ---------------- Google Sheets sync ----------------
    #: Sheet ID (URL dagi /d/<ID>/ qismi). Bo'sh bo'lsa — bot o'zi yaratadi
    #: (data/sheet_id.txt ga saqlanadi).
    GOOGLE_SHEET_ID: str = Field(default="", description="Google Sheet ID")
    #: Service account JSON fayl yo'li (base_dir ga nisbatan yoki absolut)
    GOOGLE_SA_JSON: str = Field(default="data/google_sa.json")
    #: Bot o'zi sheet yaratganda shu emailga Editor huquqi beriladi
    GOOGLE_SHEET_OWNER_EMAIL: str = Field(default="", description="Sheet egasi email")
    #: Necha daqiqada bir sync qilinadi
    SHEETS_SYNC_INTERVAL_MIN: int = Field(default=60, ge=5, le=1440)

    # =================== Validators ===================

    @field_validator("DAILY_POST_TIME", "NAMOZ_SEND_TIME")
    @classmethod
    def _validate_time(cls, v: str) -> str:
        try:
            hh, mm = map(int, v.split(":"))
            assert 0 <= hh <= 23 and 0 <= mm <= 59
        except (ValueError, AssertionError) as e:
            raise ValueError(f"Vaqt formati noto'g'ri: {v}. Kutilgan: HH:MM") from e
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        v = v.upper()
        if v not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"LOG_LEVEL noto'g'ri: {v}")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        """Heroku/boshqa provayder URL'ini SQLAlchemy async formatiga keltiradi.

        Heroku Postgres `postgres://...` beradi — SQLAlchemy buni qabul
        qilmaydi va async uchun `asyncpg` drayveri kerak. Shuning uchun:
          postgres://          -> postgresql+asyncpg://
          postgresql://        -> postgresql+asyncpg://
        SQLite va allaqachon to'g'ri URL'lar o'zgarishsiz qoladi.
        """
        v = v.strip()
        if v.startswith("postgres://"):
            v = "postgresql+asyncpg://" + v[len("postgres://"):]
        elif v.startswith("postgresql://"):
            v = "postgresql+asyncpg://" + v[len("postgresql://"):]
        # asyncpg `sslmode` query paramni tushunmaydi — SSL connect_args orqali
        # beriladi (session.py), shuning uchun URL'dan olib tashlaymiz.
        if v.startswith("postgresql+asyncpg://") and "sslmode=" in v:
            base, _, query = v.partition("?")
            params = [p for p in query.split("&") if not p.startswith("sslmode=")]
            v = base + ("?" + "&".join(params) if params else "")
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
    def namoz_hour(self) -> int:
        return int(self.NAMOZ_SEND_TIME.split(":")[0])

    @property
    def namoz_minute(self) -> int:
        return int(self.NAMOZ_SEND_TIME.split(":")[1])

    @property
    def namoz_chat_id(self) -> int | None:
        """0 — o'chiq."""
        return self.NAMOZ_CHAT_ID or None

    @property
    def web_port(self) -> int:
        """Web server porti — Heroku `$PORT` beradi, aks holda WEBAPP_PORT."""
        env_port = os.environ.get("PORT")
        if env_port and env_port.isdigit():
            return int(env_port)
        return self.WEBAPP_PORT

    @property
    def is_postgres(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")

    @property
    def cors_origins_list(self) -> list[str]:
        """WEBAPP_CORS_ORIGINS ni ro'yxatga aylantiradi."""
        raw = self.WEBAPP_CORS_ORIGINS.strip()
        if raw in ("", "*"):
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

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

    @property
    def google_sa_path(self) -> Path:
        """Service account JSON absolut yo'li."""
        p = Path(self.GOOGLE_SA_JSON)
        return p if p.is_absolute() else BASE_DIR / p

    @property
    def sheet_id_file(self) -> Path:
        """Bot o'zi yaratgan sheet ID sini saqlaydigan fayl."""
        return self.data_dir / "sheet_id.txt"

    @property
    def sheets_configured(self) -> bool:
        """Sheets sync ishlashi uchun minimal shart — SA kalit fayli mavjud."""
        return self.google_sa_path.exists()


# Global singleton — bir marta yuklanadi
_settings: Settings | None = None


def get_settings() -> Settings:
    """Settings ni lazy yuklash (test uchun ham qulay)."""
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings
