@echo off
setlocal
set PYTHONIOENCODING=utf-8
set BOT_DIR=C:\Users\suxrob\Downloads\taqvim_bot_v1\taqvim_bot
set PYTHON=%BOT_DIR%\.venv\Scripts\python.exe
set LOGDIR=%BOT_DIR%\logs

if not exist "%LOGDIR%" mkdir "%LOGDIR%"

:LOOP
echo [%date% %time%] Bot ishga tushmoqda... >> "%LOGDIR%\run_forever.log"
cd /d "%BOT_DIR%"
"%PYTHON%" -m app >> "%LOGDIR%\bot_stdout.log" 2>> "%LOGDIR%\bot_stderr.log"
echo [%date% %time%] Bot to'xtadi. 10s keyin qayta boshlanadi... >> "%LOGDIR%\run_forever.log"
timeout /t 10 /nobreak >nul
goto LOOP
