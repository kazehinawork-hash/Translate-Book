@echo off
REM ============================================
REM  TRANSLATE BOOK - 1-Click Launcher (Windows)
REM  Double-click this file to start
REM ============================================

REM Set UTF-8 for console
chcp 65001 > nul

REM Ensure running from project root
cd /d "%~dp0\.."

REM Activate virtual env if exists
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

REM Run CLI
python scripts\translate.py

REM Keep window open if error
if errorlevel 1 (
    echo.
    echo ============================================
    echo   Error occurred. See details above.
    echo ============================================
    pause
)
