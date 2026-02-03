@echo off
echo ========================================
echo  Polymarket BTC Trading Bot
echo ========================================
echo.

REM Check Mullvad
echo Checking VPN status...
curl -s --max-time 5 https://am.i.mullvad.net/connected > nul 2>&1
if errorlevel 1 (
    echo [WARNING] Could not verify Mullvad connection
    echo Make sure Mullvad VPN is connected!
    echo.
    choice /M "Continue anyway"
    if errorlevel 2 exit /b 1
)

REM Activate venv
call venv\Scripts\activate.bat

echo.
echo Starting bot in AI mode (Sonnet pre-filter + Opus 4.5 decision)
echo Press Ctrl+C to stop
echo.

REM Run the bot - PAPER mode by default for safety
python -m src.trading.live_trader --mode paper --ai --hours 8

echo.
echo Bot stopped.
pause
