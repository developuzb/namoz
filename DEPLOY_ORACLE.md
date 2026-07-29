# TAQVIMbot — Oracle Cloud "Always Free" ga deploy (24/7)

Bu yo'riqnoma botni Oracle Cloud bepul serverida doimiy (kompyuteringizga bog'liq bo'lmagan holda) ishga tushirish uchun. Bot **polling** rejimida ishlaydi — hech qanday tashqi port ochish shart emas. Ma'lumot (obunachilar, statistika) serverning doimiy diskida SQLite'da saqlanadi.

---

## 0. Nima kerak

- Oracle Cloud akkaunti (bepul, lekin ro'yxatdan o'tishda bank karta verifikatsiyasi so'raladi — pul yechilmaydi).
- Kompyuteringizdagi `.env` fayli (BOT_TOKEN va h.k.) va `data/bot.db` (mavjud ma'lumot).

---

## 1. Bepul VM yaratish

1. https://www.oracle.com/cloud/free/ — ro'yxatdan o'ting / kiring.
2. **Menu → Compute → Instances → Create instance**.
3. Sozlamalar:
   - **Image**: Canonical **Ubuntu 22.04** (yoki 24.04).
   - **Shape**: "Always Free eligible" belgisi borini tanlang.
     - Eng sodda: **VM.Standard.E2.1.Micro** (AMD, 1 GB RAM) — bot uchun yetarli.
     - Yoki **VM.Standard.A1.Flex** (ARM) 1 OCPU / 6 GB (agar mavjud bo'lsa).
   - **SSH keys**: "Generate a key pair for me" → **private key**'ni yuklab oling (masalan `ssh-key.key`). Saqlang!
4. **Create** bosing. Bir-ikki daqiqada instance "Running" bo'ladi. **Public IP** manzilini nusxa oling.

> Eslatma: 2026-yil 15-iyundan ARM (A1) bepul limiti 2 OCPU / 12 GB ga kamaydi. AMD Micro variant bundan ta'sirlanmaydi.

---

## 2. Serverga SSH orqali ulanish

Windows'da PowerShell oching (kalit yuklangan papkada):

```powershell
# Kalit huquqini to'g'rilash (bir marta)
icacls .\ssh-key.key /inheritance:r
icacls .\ssh-key.key /grant:r "$($env:USERNAME):(R)"

# Ulanish (IP ni o'zingiznikiga almashtiring)
ssh -i .\ssh-key.key ubuntu@<SERVER_IP>
```

`ubuntu` — Ubuntu image'ining standart foydalanuvchisi.

---

## 3. Repo'ni serverga olish va Docker o'rnatish

Server ichida (SSH terminalida):

```bash
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/developuzb/namoz.git ~/taqvim_bot
bash ~/taqvim_bot/deploy/setup_server.sh
```

Skript: swap yaratadi, Docker o'rnatadi, konteyner quradi. Birinchi marta `.env` yo'qligi sababli **to'xtaydi** — bu normal, 4-qadamga o'ting.

> **Agar repo private bo'lsa**, clone'da GitHub token ishlating:
> `git clone https://<GITHUB_TOKEN>@github.com/developuzb/namoz.git ~/taqvim_bot`
> (yoki GitHub'da repo'ni Public qiling).

---

## 4. `.env` va mavjud ma'lumotni serverga ko'chirish

**Kompyuteringizda** (PowerShell, repo papkasida) — serverga nusxalang:

```powershell
# .env (maxfiy token va sozlamalar)
scp -i .\ssh-key.key .\.env ubuntu@<SERVER_IP>:~/taqvim_bot/.env

# Mavjud ma'lumotlar bazasi (obunachilar, statistika)
scp -i .\ssh-key.key .\data\bot.db ubuntu@<SERVER_IP>:~/taqvim_bot/data/bot.db
```

> `.env` va `bot.db` GitHub'ga yuklanmaydi (xavfsizlik uchun gitignore'da), shuning uchun ularni qo'lda ko'chirish kerak.

---

## 5. Ishga tushirish

Server ichida skriptni qayta ishga tushiring — endi `.env` bor:

```bash
bash ~/taqvim_bot/deploy/setup_server.sh
```

Tugagach bot ishlab turadi.

---

## 6. Tekshirish va boshqarish

```bash
cd ~/taqvim_bot

sudo docker compose logs -f bot     # jonli loglar (chiqish: Ctrl+C)
sudo docker compose ps              # holat
sudo docker compose restart bot     # qayta ishga tushirish
sudo docker compose down            # to'xtatish
```

Bot xato bilan to'xtasa Docker uni avtomatik qayta ishga tushiradi (`restart: unless-stopped`), va server qayta yoqilsa ham o'zi ko'tariladi.

---

## 7. Keyinchalik kodni yangilash

GitHub'ga yangi o'zgarish push qilganingizdan so'ng, serverda:

```bash
cd ~/taqvim_bot
git pull
sudo docker compose up -d --build
```

Migratsiyalar konteyner ishga tushganda avtomatik qo'llanadi (`alembic upgrade head`).

---

## Qo'shimcha eslatmalar

- **Mini-app (WebApp)**: u tashqi HTTPS URL talab qiladi. Botning asosiy (namoz vaqtlari) funksiyasi mini-appsiz ham to'liq ishlaydi. Mini-app kerak bo'lsa, domen + reverse-proxy (Caddy/Nginx) sozlash kerak — alohida bosqich.
- **Zaxira (backup)**: `data/bot.db` ni vaqti-vaqti bilan o'zingizga yuklab oling:
  `scp -i .\ssh-key.key ubuntu@<SERVER_IP>:~/taqvim_bot/data/bot.db .\backups\`
- **Xavfsizlik**: `.env` ichidagi `BOT_TOKEN` maxfiy. Uni hech kimga bermang va GitHub'ga qo'ymang.
