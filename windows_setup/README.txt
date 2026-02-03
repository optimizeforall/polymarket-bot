========================================
 POLYMARKET BTC TRADING BOT - WINDOWS
========================================

REQUIREMENTS:
- Python 3.10+ (https://python.org)
- Mullvad VPN (https://mullvad.net)
- Your Polymarket credentials

QUICK START:
1. Install Python (check "Add to PATH")
2. Install Mullvad VPN
3. Copy entire polymarket-bot folder to your PC
4. Run: setup.bat (one time)
5. Edit .env file with your credentials
6. Connect Mullvad VPN
7. Run: test_connection.bat (verify everything works)
8. Run: run_bot.bat (paper trading) or run_live.bat (real money)

FILES:
- setup.bat         : One-time setup (creates venv, installs deps)
- test_connection.bat: Test VPN and API connections
- run_bot.bat       : Run in PAPER mode (no real money)
- run_live.bat      : Run in LIVE mode (real money!)
- .env.example      : Template for credentials

.ENV FILE (create from .env.example):
POLYMARKET_PRIVATE_KEY=your_private_key
POLYMARKET_FUNDER_ADDRESS=your_wallet_address
OPENROUTER_API_KEY=sk-or-v1-...
TELEGRAM_BOT_TOKEN=your_bot_token (optional)
TELEGRAM_CHAT_ID=your_chat_id (optional)

TRADING SETTINGS (in src/trading/live_trader.py):
- INITIAL_CAPITAL = 100.0  (your starting balance)
- MAX_POSITION_PCT = 0.07  (7% max per trade = $7)
- CONSECUTIVE_LOSS_HALT = 3 (stop after 3 losses)
- DAILY_TRADE_LIMIT = 8

AI MODE:
The bot uses a two-stage AI system:
1. Sonnet 3.5 pre-filters opportunities (cheap)
2. Opus 4.5 makes final decision (smart)

Only trades when Opus says HIGH or MEDIUM confidence.

SUPPORT:
Check the main README.md for full documentation.

========================================
 IMPORTANT: Always connect Mullvad VPN
 before running live trades!
========================================
