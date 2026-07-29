#!/usr/bin/env bash
# =====================================================================
# TAQVIMbot — Oracle Cloud (Ubuntu) serverda bir buyruq bilan o'rnatish
# Ishlatish:  bash setup_server.sh
# =====================================================================
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/developuzb/namoz.git}"
APP_DIR="${APP_DIR:-$HOME/taqvim_bot}"

echo "============================================================"
echo "  TAQVIMbot serverga o'rnatilmoqda"
echo "  Repo : $REPO_URL"
echo "  Papka: $APP_DIR"
echo "============================================================"

echo "==> 1/6 Tizim paketlarini yangilash..."
sudo apt-get update -y

echo "==> 2/6 Swap yaratish (kichik RAM li instance uchun)..."
if ! sudo swapon --show 2>/dev/null | grep -q '/swapfile'; then
    sudo fallocate -l 2G /swapfile 2>/dev/null || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "    Swap yaratildi (2GB)."
else
    echo "    Swap allaqachon mavjud."
fi

echo "==> 3/6 Docker o'rnatish..."
if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER" || true
    echo "    Docker o'rnatildi."
else
    echo "    Docker allaqachon mavjud."
fi
sudo systemctl enable --now docker

echo "==> 4/6 Repo klonlash / yangilash..."
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" pull --ff-only
else
    git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

echo "==> 5/6 .env faylini tekshirish..."
if [ ! -f .env ]; then
    echo ""
    echo "  ⚠️  .env fayli topilmadi!"
    echo "  Quyidagini bajaring, so'ng skriptni qayta ishga tushiring:"
    echo "      cd $APP_DIR"
    echo "      cp .env.example .env"
    echo "      nano .env      # BOT_TOKEN, ADMIN_IDS va boshqalarni kiriting"
    echo ""
    exit 1
fi

echo "==> 6/6 Konteyner qurish va ishga tushirish..."
sudo docker compose up -d --build

echo ""
echo "============================================================"
echo "  ✅ Tayyor! Bot ishlayapti va server qayta yoqilsa ham"
echo "     avtomatik ishga tushadi (restart: unless-stopped)."
echo ""
echo "  Loglar     : sudo docker compose logs -f bot"
echo "  Holat      : sudo docker compose ps"
echo "  Qayta start: sudo docker compose restart bot"
echo "  Yangilash  : git pull && sudo docker compose up -d --build"
echo "============================================================"
