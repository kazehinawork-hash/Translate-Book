@echo off
chcp 65001 >nul
title Pull Translate Book from GitHub

echo ==========================================
echo  PULL TRANSLATE BOOK FROM GITHUB
echo  Repo: https://github.com/kazehinawork-hash/Translate-Book.git
echo ==========================================
echo.

REM Check if git is installed
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Git not found. Install from: https://git-scm.com/download/win
    pause
    exit /b 1
)

REM Check if git repo exists
if not exist ".git" (
    echo [ERROR] No git repository found here.
    echo Run push_to_github.bat to initialize, or:
    echo   git clone https://github.com/kazehinawork-hash/Translate-Book.git .
    pause
    exit /b 1
)

REM Check current branch
for /f "tokens=*" %%i in ('git branch --show-current') do set CURRENT_BRANCH=%%i
echo [1/4] Current branch: %CURRENT_BRANCH%

REM Check for uncommitted changes
git status --porcelain >nul 2>nul
if %errorlevel% equ 0 (
    git diff --quiet
    if %errorlevel% neq 0 (
        echo [2/4] [WARNING] Uncommitted changes detected!
        echo.
        git status --short
        echo.
        set /p CHOICE="Continue with pull? (y/n): "
        if /i not "%CHOICE%"=="y" (
            echo Pull cancelled.
            pause
            exit /b 0
        )
    ) else (
        echo [2/4] No uncommitted changes.
    )
)

REM Fetch latest
echo [3/4] Fetching latest from GitHub...
git fetch origin

REM Pull with rebase (keep history clean)
echo [4/4] Pulling with rebase...
git pull origin %CURRENT_BRANCH% --rebase

echo.
echo ==========================================
if %errorlevel% equ 0 (
    echo [SUCCESS] Pull completed!
    echo.
    git log --oneline -5
) else (
    echo [ERROR] Pull failed. May have conflicts.
    echo Run: git status  to see conflicted files
    echo Then: git add .  and  git rebase --continue
)
echo ==========================================
echo.
pause
