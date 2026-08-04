@echo off
cd /d "%~dp0"
dotnet run
if errorlevel 1 (
    echo.
    echo Loi! Nhan phim bat ky de thoat...
    pause >nul
)
