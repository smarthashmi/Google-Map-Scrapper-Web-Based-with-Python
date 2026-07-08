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

REM Use project virtual environment for reliable dependencies
if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

set PYTHON=venv\Scripts\python.exe

REM If server is already running, just open the browser
powershell -NoProfile -Command "try { (Invoke-WebRequest -Uri 'http://127.0.0.1:5050/login' -UseBasicParsing -TimeoutSec 2).StatusCode | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 (
    echo Server is already running at http://127.0.0.1:5050
    start http://127.0.0.1:5050
    pause
    exit /b 0
)

echo Checking and installing dependencies...
"%PYTHON%" -m app.setup_deps
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

"%PYTHON%" -m app.web

pause
