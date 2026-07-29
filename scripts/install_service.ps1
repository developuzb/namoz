# TAQVIMbot — Windows Task Scheduler ga ro'yxatdan o'tkazish
# Administrator sifatida ishga tushiring!

$TaskName   = "TaqvimBot_24_7"
$ScriptPath = "C:\Users\suxrob\Downloads\taqvim_bot_v1\taqvim_bot\scripts\run_forever.ps1"
$UserName   = $env:USERNAME

Write-Host "=== TAQVIMbot Task Scheduler o'rnatilmoqda ===" -ForegroundColor Cyan
Write-Host "Task nomi : $TaskName"
Write-Host "Foydalanuvchi: $UserName"
Write-Host ""

# Eski taskni o'chirish (mavjud bo'lsa)
schtasks /Delete /TN $TaskName /F 2>$null | Out-Null

# Yangi task yaratish: tizim yoqilganda ishga tushadi
$action  = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$ScriptPath`""

$trigger = New-ScheduledTaskTrigger -AtStartup

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

$principal = New-ScheduledTaskPrincipal `
    -UserId $UserName `
    -LogonType Interactive `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

Write-Host "✅ Task yaratildi: '$TaskName'" -ForegroundColor Green
Write-Host ""
Write-Host "Hozir ishga tushirishni xohlaysizmi? (Y / N)" -NoNewline
$ans = Read-Host " "
if ($ans -match '^[Yy]') {
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "✅ Bot ishga tushirildi!" -ForegroundColor Green
}

Write-Host ""
Write-Host "Boshqarish buyruqlari:" -ForegroundColor Yellow
Write-Host "  To'xtatish : schtasks /End /TN $TaskName"
Write-Host "  Boshlash   : schtasks /Run /TN $TaskName"
Write-Host "  O'chirish  : schtasks /Delete /TN $TaskName /F"
