@echo off
cd /d "C:\Users\daiki\Desktop\000_Uematsu\003_事業\08_ベースボールデータ分析サイト\02_開発環境\webapp"

echo === Checking git status ===
git status

echo.
echo === Setting git config ===
git config user.email "d.uematsu@transdata.tv"
git config user.name "Daiki Uematsu"

echo.
echo === Checking if already a git repo ===
git rev-parse --git-dir 2>nul
if errorlevel 1 (
    echo Initializing git repo...
    git init -b main
    git remote add origin https://github.com/du0000du/baseballab-com.git
) else (
    echo Already a git repo.
    git remote -v
)

echo.
echo === Fetching remote ===
git fetch origin 2>nul

echo.
echo === Adding all files ===
git add -A

echo.
echo === Committing ===
git commit -m "feat: initialize Astro project with Cloudflare Pages deploy workflow"

echo.
echo === Pushing to main ===
git push -u origin main

echo.
echo === Done! Press any key to close. ===
pause
