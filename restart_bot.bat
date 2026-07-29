@echo off
cd /d "%~dp0"
echo ============================================
echo   TAQVIMbot - qayta ishga tushirish
echo ============================================
echo [1/3] Eski bot jarayoni to'xtatilmoqda...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and ($_.CommandLine -match 'taqvim' -or $_.CommandLine -match '-m app') } | ForEach-Object { Write-Host ('  PID ' + $_.ProcessId + ' toxtatildi'); Stop-Process -Id $_.ProcessId -Force }"
timeout /t 2 /nobreak >nul
echo [2/3] Kutubxonalar tekshirilmoqda (gspread va h.k.)...
where uv >nul 2>&1 && uv sync || .venv\Scripts\python.exe -m pip install -q gspread

echo [3/3] Bot yangi kod bilan ishga tushirilmoqda...
start "TAQVIMbot" cmd /k .venv\Scripts\python.exe -m app
echo Tayyor! Bot alohida oynada ishlayapti.
echo Endi Telegram'da /test_namoz yuborib tekshiring.
pause
