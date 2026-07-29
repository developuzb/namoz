# TAQVIMbot — 24/7 auto-restart wrapper
# Windows yoqilganda registry orqali avtomatik ishga tushadi.
# Bot ishdan chiqsa — 10 soniya kutib qayta ishga tushiradi.

$BotDir  = "C:\Users\suxrob\Downloads\taqvim_bot_v1\taqvim_bot"
$Python  = "$BotDir\.venv\Scripts\python.exe"
$LogDir  = "$BotDir\logs"
$LogFile = "$LogDir\run_forever.log"

$env:PYTHONIOENCODING = "utf-8"
Set-Location $BotDir

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

function Write-Log($msg) {
    $ts   = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $msg"
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

Write-Log "=== TAQVIMbot run_forever ishga tushdi ==="

$attempt = 0
while ($true) {
    $attempt++
    Write-Log "Urinish #$attempt — bot ishga tushmoqda..."

    # Oldingi python jarayonlarini tozalash
    Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2

    # Botni ishga tushirish va tugashini kutish
    $proc = Start-Process `
        -FilePath $Python `
        -ArgumentList "-m", "app" `
        -WorkingDirectory $BotDir `
        -RedirectStandardOutput "$LogDir\bot_stdout.log" `
        -RedirectStandardError  "$LogDir\bot_stderr.log" `
        -NoNewWindow `
        -PassThru

    Write-Log "Bot PID=$($proc.Id) ishga tushdi"

    # Bot tugaguncha kutish (polling, har 5 soniya)
    while (-not $proc.HasExited) {
        Start-Sleep -Seconds 5
    }

    $exitCode = $proc.ExitCode
    Write-Log "Bot PID=$($proc.Id) to'xtadi (exit=$exitCode). 10s keyin qayta boshlanadi..."
    Start-Sleep -Seconds 10
}
