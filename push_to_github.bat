@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo === GitHub'ga push qilinmoqda ===
echo Repo: %cd%
echo.

REM Eski stale lock fayllarni tozalash
if exist ".git\index.lock" del /f /q ".git\index.lock"

echo --- git add -A ---
git add -A

echo --- git commit ---
git commit -m "chore: sync local o'zgarishlar — kanal grafikasi redizayn, scripts, backups, utils"

echo --- git push (origin main) ---
git push -u origin main

echo.
echo === Tugadi. Yuqorida xato bo'lmasa, push muvaffaqiyatli. ===
pause
