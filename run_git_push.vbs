Dim oShell, oExec, sOutput, sCmd
Set oShell = CreateObject("WScript.Shell")

Dim sDir
sDir = "C:\Users\daiki\Desktop\000_Uematsu\003_事業\08_ベースボールデータ分析サイト\02_開発環境\webapp"

' Run git commands via PowerShell, show output in a window
sCmd = "powershell.exe -NoExit -Command """ & _
    "cd '" & sDir & "'; " & _
    "git config user.email 'd.uematsu@transdata.tv'; " & _
    "git config user.name 'Daiki Uematsu'; " & _
    "if (-not (Test-Path '.git')) { git init -b main; git remote add origin 'https://github.com/du0000du/baseballab-com.git' } else { Write-Host 'Already a git repo' }; " & _
    "git fetch origin 2>&1; " & _
    "git add -A; " & _
    "git commit -m 'feat: initialize Astro project with Cloudflare Pages deploy workflow'; " & _
    "git push -u origin main; " & _
    "Write-Host 'DONE - press any key'; " & _
    "pause" & _
    """"

oShell.Run sCmd, 1, False
