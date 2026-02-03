# 🚀 Polymarket BTC Trading Bot - Quick Start

## What You Have

A working autonomous trading bot that:
- ✅ Monitors BTC price in real-time
- ✅ Generates BUY/SELL/HOLD signals using RSI, VWAP, and momentum
- ✅ Finds active BTC 15-minute markets on Polymarket automatically
- ✅ Executes paper trades (and can do live trades)
- ✅ Sends Telegram notifications (when configured)
- ✅ Respects hard risk limits (max 10% per trade, daily drawdown limits)

## Quick Commands

### 1. Start Price Logger (Required - Run in Background)
```bash
cd /home/ubuntu/polymarket-bot
source venv/bin/activate
python main.py
```
Keep this running in a separate terminal - it collects the price data the bot needs.

### 2. Check Current Markets
```bash
python src/market_finder.py
```
Shows active BTC 15-min markets and their current prices.

### 3. Run Paper Trading (Safe - No Real Money)
```bash
# 1 hour test
python run_trader.py

# Overnight (8 hours)
python run_trader.py --hours 8
```

### 4. Run LIVE Trading (Real Money!)
```bash
# ⚠️ WARNING: This uses real money!
python run_trader.py --live --hours 8
```

## Setup Telegram Notifications (Recommended)

1. Open Telegram, search for `@BotFather`
2. Send `/newbot` and follow the prompts
3. Copy the bot token
4. Search for `@userinfobot`, send `/start` to get your chat ID
5. Edit `.env`:
```
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

## How It Works

1. **Price Logger** (`main.py`) - Collects BTC prices every 5 seconds
2. **Signal Generator** - Analyzes RSI, VWAP deviation, and momentum
3. **Market Finder** - Finds active 15-min BTC Up/Down markets on Polymarket
4. **Live Trader** - Executes trades based on signals

### Signal Rules

**BUY (bet UP)** when 2+ of these align:
- Price > VWAP + 0.15%
- RSI between 50-70
- Positive momentum

**SELL (bet DOWN)** when 2+ of these align:
- Price < VWAP - 0.15%
- RSI between 30-50
- Negative momentum

### Risk Limits (Hard-Coded)
- Max 10% of account per trade ($50 on $500)
- Max 2 concurrent positions
- 10% daily drawdown = trading stops
- 5 consecutive losses = position size reduced 50%
- Max 8 trades per day

## File Structure

```
polymarket-bot/
├── run_trader.py          # Main entry point
├── main.py                # Price logger
├── .env                   # Your credentials
├── data/
│   ├── btc_prices.csv     # Price data
│   ├── signals.csv        # Signal history
│   └── live_trades.csv    # Trade log
└── src/
    ├── market_finder.py   # Find Polymarket markets
    └── trading/
        ├── live_trader.py     # Main trading bot
        ├── signal_generator.py # Signal logic
        └── indicators.py      # RSI, VWAP, etc.
```

## Overnight Mode

To run overnight and get updates:

```bash
# Terminal 1: Price logger
python main.py

# Terminal 2: Trading bot (8 hours)
python run_trader.py --hours 8
```

The bot will:
- Check for signals every 60 seconds
- Trade during optimal windows (minutes 2-10 of each 15-min interval)
- Send hourly summaries to Telegram
- Send alerts for every trade
- Stop automatically after the specified duration

## Troubleshooting

**"No price data"** - Run `python main.py` first and wait a few minutes

**"No market found"** - Markets are created every 15 minutes, wait for the next one

**"Telegram not working"** - Check your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env

## Cost Note

This bot does NOT use OpenClaw/Opus 4.5 for trading decisions. It runs locally using simple technical indicators, so there's no per-request AI cost. The only costs are:
- Polymarket trading fees
- Your actual trades (wins/losses)
