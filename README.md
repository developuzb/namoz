# 🕌 TAQVIMbot

**O'zbekiston namoz vaqtlari Telegram boti** — kanal va shaxsiy obunachilarga avtomatik namoz vaqtlari, eslatmalar va statistika.

---

## ✨ Xususiyatlari

- 📅 **Avtomatik kunlik post** — har kuni belgilangan vaqtda kanalga rasm + caption
- 🌍 **Ko'p hudud** — viloyat va tumanlar bo'yicha alohida sozlash
- 👤 **DM obuna** — foydalanuvchilar shaxsiy chatda obuna bo'lib eslatma olishi mumkin
- 🌙 **Nafl vaqtlari** — Tahajjud, Ishroq, Zuho, Avvobiyn avtomatik hisoblanadi
- 🕋 **Hijriy sana** — O'zbekcha oy nomlari bilan
- 🛠 **Admin paneli** — bot ichida (FSM bilan): hudud, kanal, masjid vaqtlari, statistika
- 📊 **Statistika** — har bir event DB ga yoziladi
- 🔄 **Provider fallback** — `islomapi.uz` asosiy, `praytime.uz` zaxira
- 🐳 **Docker ready** — `docker compose up` bilan ishga tushadi

---

## 🚀 Tezkor boshlash

### 1. Talablar

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (paket menejeri)
- Telegram Bot Token ([@BotFather](https://t.me/BotFather))

### 2. O'rnatish

```bash
git clone <repo-url>
cd taqvim_bot

# Bog'liqliklarni o'rnatish
uv sync

# .env ni sozlash
cp .env.example .env
nano .env   # BOT_TOKEN va ADMIN_IDS ni kiritish

# DB migrasiyasi
uv run alembic upgrade head

# Ishga tushirish
uv run python -m app
```

### 3. Docker bilan

```bash
cp .env.example .env
# .env ni to'ldiring
docker compose up -d
docker compose logs -f bot
```

---

## 📁 Loyiha tuzilishi

```
app/
├── core/          # Konfiguratsiya, log, constantalar
├── db/            # Modellar va repository lar
├── services/      # Biznes mantiq (provider, calculator, image, ...)
├── bot/           # Telegram qatlam (handlers, keyboards, FSM)
├── scheduler/     # APScheduler vazifalari
└── utils/         # Yordamchi funksiyalar
```

To'liq tuzilish — [`docs/architecture.md`](docs/architecture.md) (TODO).

---

## 🛠 Admin buyruqlari

| Buyruq | Vazifa |
|--------|--------|
| `/admin` | Admin paneli (FSM menyu) |
| `/stats` | Umumiy statistika |
| `/test_post <hudud>` | Test post yuborish |
| `/broadcast` | Hammaga xabar |

---

## 🧪 Test va lint

```bash
# Linter
uv run ruff check .
uv run ruff format .

# Type-check
uv run mypy app

# Testlar
uv run pytest
uv run pytest --cov=app
```

---

## 📜 Litsenziya

MIT
