# 🚀 Deploy — Heroku (bot + API) + GitHub Pages (Mini App)

Arxitektura ikkiga bo'lingan:

| Qism | Qayerda | Nima |
|------|---------|------|
| **Mini App frontend** (statik) | GitHub Pages (`/docs`) | `index.html`, `styles.css`, `app.js`, `emojis/` |
| **Bot + API + scheduler** | Heroku (bitta `web` dyno) | polling, kunlik post, `/api/*`, Postgres |

Frontend brauzerda ishlaydi va API'ni Heroku'dan chaqiradi (CORS orqali).

---

## 1️⃣ Heroku (bot + API)

> ⚠️ Heroku 2022-dan beri bepul emas. Kerak: **Basic dyno ~$7/oy** (Eco uxlaydi — polling to'xtaydi) + **Postgres `essential-0` ~$5/oy** + xalqaro karta.

### CLI orqali

```bash
heroku login
heroku create taqvimbot                     # nom band bo'lsa boshqa nom
heroku addons:create heroku-postgresql:essential-0 -a taqvimbot

# Config (DATABASE_URL Postgres addon tomonidan avtomatik qo'yiladi)
heroku config:set -a taqvimbot \
  BOT_TOKEN=123456:ABC... \
  ADMIN_IDS=111111111 \
  TZ=Asia/Tashkent \
  WEBAPP_URL=https://developuzb.github.io/namoz/ \
  WEBAPP_CORS_ORIGINS=https://developuzb.github.io

git push heroku main                        # yoki Dashboard → GitHub auto-deploy
heroku ps:scale web=1 -a taqvimbot          # Basic dyno
heroku logs --tail -a taqvimbot
```

- `release: alembic upgrade head` (Procfile) — har deploy'da migratsiyalarni qo'llaydi.
- `TZ=Asia/Tashkent` **muhim** — aks holda kunlik post/eslatma vaqtlari UTC bo'ladi.

### Dashboard orqali (kartasiz push, GitHub'dan)

1. [dashboard.heroku.com](https://dashboard.heroku.com) → **New → Create new app**.
2. **Resources → Add-ons →** `Heroku Postgres` (`essential-0`).
3. **Settings → Config Vars →** yuqoridagi o'zgaruvchilarni qo'shing.
4. **Deploy → GitHub →** `developuzb/namoz` ni ulang → **Enable Automatic Deploys** (branch: `main`).
5. **Deploy Branch** bosing.

Heroku app URL'ini oling: `heroku info -a taqvimbot` yoki Dashboard'dan
(masalan `https://taqvimbot-xxxx.herokuapp.com`).

---

## 2️⃣ GitHub Pages (Mini App frontend)

1. Repo → **Settings → Pages**.
2. **Source:** `Deploy from a branch` → **Branch:** `main` → **Folder:** `/docs` → **Save**.
3. Bir-ikki daqiqada manzil tayyor: **`https://developuzb.github.io/namoz/`**

### Muhim: API manzilini ulash

`docs/config.js` faylini oching va Heroku URL'ingizni yozing (oxirida `/` yo'q):

```js
window.API_BASE = "https://taqvimbot-xxxx.herokuapp.com";
```

Commit + push qiling — Pages avtomatik yangilanadi.

> Agar CORS xatosi chiqsa: Heroku'dagi `WEBAPP_CORS_ORIGINS` aynan
> `https://developuzb.github.io` (oxirida `/` yo'q) ekaniga ishonch hosil qiling.

---

## 3️⃣ BotFather — Mini App tugmasini ulash

1. [@BotFather](https://t.me/BotFather) → `/mybots` → botni tanlang.
2. **Bot Settings → Menu Button → Configure menu button** → URL:
   `https://developuzb.github.io/namoz/`

Yoki `WEBAPP_URL` sozlangani uchun bot ichidagi tugmalar ham shu manzilga
ishora qiladi.

---

## 🔍 Tekshirish

```bash
# API tirikmi?
curl https://taqvimbot-xxxx.herokuapp.com/api/health
# → {"ok": true, ...}

# Mini App'ni Telegram'dan oching → vaqtlar, qibla, oyat ko'rinishi kerak.
```

## ⚙️ Config o'zgaruvchilari (to'liq)

| O'zgaruvchi | Majburiy | Izoh |
|-------------|----------|------|
| `BOT_TOKEN` | ✅ | BotFather tokeni |
| `DATABASE_URL` | ✅ (avto) | Postgres addon qo'yadi (`postgres://…` → kod avtomatik `postgresql+asyncpg://`ga o'giradi) |
| `TZ` | ✅ | `Asia/Tashkent` |
| `WEBAPP_URL` | ⬜ | `https://developuzb.github.io/namoz/` |
| `WEBAPP_CORS_ORIGINS` | ⬜ | `https://developuzb.github.io` |
| `ADMIN_IDS` | ⬜ | Vergul bilan admin ID'lar |
| `DAILY_POST_TIME` | ⬜ | `06:00` |
| `NAMOZ_CHAT_ID` | ⬜ | Qashqadaryo plakat kanali |

## 📝 Eslatmalar

- **DB Heroku Postgres'da** — dyno restart bo'lsa ham ma'lumot saqlanadi.
- **Kunlik SQLite backup** (`backup.py`) Postgres'da avtomatik o'tkazib
  yuboriladi (faqat SQLite uchun edi).
- Lokal dev hamon SQLite bilan ishlaydi (`.env`da `DATABASE_URL` qo'yilmasa).
