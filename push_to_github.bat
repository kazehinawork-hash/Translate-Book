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
    echo [ERROR] Git khong tim thay. Cai dat tai: https://git-scm.com/download/win
    pause
    exit /b 1
)

REM Initialize git repo if not exists
if not exist ".git" (
    echo [1/6] Khoi tao git repository...
    git init
    if %errorlevel% neq 0 (
        echo [ERROR] Khong the khoi tao git repo
        pause
        exit /b 1
    )
) else (
    echo [1/6] Git repository da ton tai
)

REM Configure user (only if not set)
git config user.name >nul 2>nul
if %errorlevel% neq 0 (
    echo [2/6] Cau hinh git user...
    set /p GIT_NAME="Nhap ten cua ban (git user.name): "
    set /p GIT_EMAIL="Nhap email cua ban (git user.email): "
    git config user.name "%GIT_NAME%"
    git config user.email "%GIT_EMAIL%"
) else (
    echo [2/6] Git user da cau hinh: %git config user.name%
)

REM Add remote origin
echo [3/6] Kiem tra remote origin...
git remote get-url origin >nul 2>nul
if %errorlevel% neq 0 (
    echo Them remote origin...
    git remote add origin https://github.com/kazehinawork-hash/Translate-Book.git
) else (
    echo Remote origin da ton tai
    git remote set-url origin https://github.com/kazehinawork-hash/Translate-Book.git
)

REM Add files (respecting .gitignore)
echo [4/6] Them file vao git (tuan thu .gitignore)...
git add .

REM Commit
echo [5/6] Commit thay doi...
git commit -m "feat: initial commit - Translate Book project structure"
if %errorlevel% neq 0 (
    echo [INFO] Khong co thay doi moi de commit (co the da commit truoc do)
)

REM Push to GitHub
echo [6/6] Push len GitHub...
git branch -M main
git push -u origin main

echo.
echo ==========================================
if %errorlevel% equ 0 (
    echo [SUCCESS] Da push thanh cong len GitHub!
    echo Repo: https://github.com/kazehinawork-hash/Translate-Book
) else (
    echo [ERROR] Push that bai. Kiem tra:
    echo   - Co internet khong
    echo   - Repo tren GitHub da ton tai chua
    echo   - Co quyen push khong (token/SSH key)
    echo   - Co can login GitHub CLI khong: gh auth login
)
echo ==========================================
echo.
pause