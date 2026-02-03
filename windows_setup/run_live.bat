@echo off
echo ========================================
echo  Polymarket BTC Trading Bot - LIVE MODE
echo ========================================
echo.
echo [WARNING] This will trade REAL MONEY!
echo.

REM Check Mullvad
echo Checking VPN status...
curl -s --max-time 5 https://am.i.mullvad.net/connected 2>nul | findstr "You are connected" >nul
if errorlevel 1 (
    echo [ERROR] Mullvad VPN is NOT connected!
    echo Please connect Mullvad before running live trades.
    pause
    exit /b 1
)
echo [OK] Mullvad VPN connected
echo.

REM Double confirmation
echo Are you sure you want to trade with REAL money?
choice /M "Type Y to confirm LIVE trading"
if errorlevel 2 (
    echo Cancelled.
    pause
    exit /b 0
)

REM Activate venv
call venv\Scripts\activate.bat

echo.
echo Starting LIVE trading bot...
echo - Mode: LIVE (real money)
echo - AI: Sonnet 3.5 pre-filter + Opus 4.5 decision
echo - Duration: 8 hours
echo - Max position: 7%% ($7 on $100)
echo.
echo Press Ctrl+C to stop
echo.

python -m src.trading.live_trader --mode live --ai --hours 8

echo.
echo Bot stopped.
pause
