@echo off
title Business Scraper
cd /d "%~dp0"

echo ========================================
echo   Business Scraper - Starting Server
echo ========================================
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Please install Python 3.10+ and try again.
    pause
    exit /b 1
)

echo Checking and installing dependencies...
python -m app.setup_deps
if %errorlevel% neq 0 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Starting web server at http://127.0.0.1:5050
echo Browser will open automatically.
echo.
echo Press Ctrl+C to stop the server.
echo.

python -m app.web

pause
