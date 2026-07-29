#!/bin/sh
# TAQVIMbot — konteyner entrypoint.
# Bot ishga tushishidan oldin DB migratsiyalarini qo'llaydi.
set -e

echo "[entrypoint] Alembic migratsiya: upgrade head ..."
alembic upgrade head

echo "[entrypoint] Bot ishga tushmoqda ..."
exec python -m app
