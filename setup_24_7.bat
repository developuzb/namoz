@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM ============================================================
REM  TAQVIMbot — 24/7 avtoyuklash o'rnatuvchi
REM  Ikki marta bosing. UAC oynasi chiqsa "Ha" / "Yes" bosing.
REM ============================================================

REM --- Administrator huquqini tekshirish, bo'lmasa qayta so'rash (UAC) ---
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Administrator huquqi so'ralmoqda... UAC oynasida "Ha" / "Yes" ni bosing.
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo ============================================================
echo   TAQVIMbot 24/7 avtoyuklash o'rnatilmoqda...
echo ============================================================
echo.

REM --- Task Scheduler ga ro'yxatdan o'tkazish (ichki prompt N bilan o'tkaziladi) ---
echo N | powershell -ExecutionPolicy Bypass -File "%~dp0scripts\install_service.ps1"

echo.
echo --- Bot hozir ishga tushirilmoqda ---
schtasks /Run /TN "TaqvimBot_24_7"

echo.
echo ============================================================
echo   Tayyor!
echo   - Bot hozir fon rejimida ishlayapti.
echo   - Windows har yoqilganda avtomatik ishga tushadi.
echo.
echo   Holatni ko'rish : schtasks /Query /TN "TaqvimBot_24_7"
echo   To'xtatish      : schtasks /End  /TN "TaqvimBot_24_7"
echo   Qayta boshlash  : schtasks /Run  /TN "TaqvimBot_24_7"
echo   Loglar          : logs\bot_stdout.log  va  logs\run_forever.log
echo ============================================================
pause
