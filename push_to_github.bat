@echo off
chcp 65001 >nul
title Push Translate Book to GitHub

echo ==========================================
echo  PUSH TRANSLATE BOOK TO GITHUB
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

REM Initialize git repo if not exists
if not exist ".git" (
    echo [1/6] Initializing git repository...
    git init
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to initialize git repo
        pause
        exit /b 1
    )
) else (
    echo [1/6] Git repository already exists
)

REM Configure user (only if not set)
git config user.name >nul 2>nul
if %errorlevel% neq 0 (
    echo [2/6] Configuring git user...
    set /p GIT_NAME="Enter your name (git user.name): "
    set /p GIT_EMAIL="Enter your email (git user.email): "
    git config user.name "%GIT_NAME%"
    git config user.email "%GIT_EMAIL%"
) else (
    for /f "delims=" %%a in ('git config user.name') do set GIT_USER=%%a
    echo [2/6] Git user configured: %GIT_USER%
)

REM Add remote origin
echo [3/6] Checking remote origin...
git remote get-url origin >nul 2>nul
if %errorlevel% neq 0 (
    echo Adding remote origin...
    git remote add origin https://github.com/kazehinawork-hash/Translate-Book.git
) else (
    echo Remote origin already exists
    git remote set-url origin https://github.com/kazehinawork-hash/Translate-Book.git
)

REM Add files (respecting .gitignore)
echo [4/6] Adding files to git (respects .gitignore)...
git add .

REM Commit
echo [5/6] Committing changes...
git commit -m "feat: initial commit - Translate Book project structure"
if %errorlevel% neq 0 (
    echo [INFO] No new changes to commit (may have been committed already)
)

REM Push to GitHub
echo [6/6] Pushing to GitHub...
git branch -M main
git push -u origin main

echo.
echo ==========================================
if %errorlevel% equ 0 (
    echo [SUCCESS] Pushed to GitHub successfully!
    echo Repo: https://github.com/kazehinawork-hash/Translate-Book
) else (
    echo [ERROR] Push failed. Check:
    echo   - Internet connection
    echo   - GitHub repository exists
    echo   - Push permissions (token/SSH key)
    echo   - Login with GitHub CLI: gh auth login
)
echo ==========================================
echo.
pause
