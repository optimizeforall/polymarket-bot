@echo off
echo ========================================
echo  Polymarket Trading Bot - Windows Setup
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! 
    echo Please install Python 3.10+ from https://python.org
    echo Make sure to check "Add Python to PATH" during install
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create venv
    pause
    exit /b 1
)

echo [OK] Virtual environment created
echo.

REM Activate and install dependencies
echo Installing dependencies (this may take a minute)...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Copy your .env file to this folder (or edit .env.example)
echo 2. Connect Mullvad VPN
echo 3. Run: run_bot.bat
echo.
pause
