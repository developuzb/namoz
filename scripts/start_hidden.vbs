' TAQVIMbot — ko'rinmas oynada ishga tushirish
' Bu fayl Windows Startup papkasiga qo'yiladi

Dim WShell
Set WShell = CreateObject("WScript.Shell")

' 0 = oyna ko'rinmaydi (SW_HIDE)
WShell.Run "cmd.exe /c """ & "C:\Users\suxrob\Downloads\taqvim_bot_v1\taqvim_bot\scripts\run_bot.bat" & """", 0, False

Set WShell = Nothing
