# Polymarket BTC Trading Bot

An AI-powered autonomous trading bot for Bitcoin 15-minute prediction markets on Polymarket. Uses advanced AI models (Claude Sonnet 3.5 + Opus 4.5) for signal generation with comprehensive market analysis, risk management, and live trading capabilities.

## 🚀 Features

### AI-Powered Signal Generation
- **Two-Stage AI System**: Sonnet 3.5 pre-filters opportunities → Opus 4.5 makes final decision
- **Comprehensive Context**: Multi-timeframe analysis (1h, 4h, 24h, 3d), order book microstructure, sentiment analysis
- **Visual Chart Analysis**: Generates and analyzes 15m, 1h, 4h candlestick charts with indicators
- **Smart Filtering**: Only trades when AI has HIGH or MEDIUM confidence with clear edge

### Live Trading
- **Polymarket CLOB API Integration**: Direct order placement and execution
- **Real-Time Balance**: Fetches actual USDC balance from Polygon blockchain
- **Residential Proxy Support**: IPRoyal proxy integration to bypass Cloudflare blocking
- **Order Management**: GTC orders with proper signature handling for Magic Link accounts

### Risk Management
- **Position Sizing**: 7% max per trade (configurable)
- **Loss Protection**: Stops after 3 consecutive losses
- **Drawdown Limits**: 10% daily drawdown protection
- **Trade Limits**: 8 trades per day maximum
- **Conservative Mode**: Reduces position size by 50% after 2 losses

### Monitoring & Notifications
- **Telegram Integration**: Real-time trade alerts with market details
- **CSV Logging**: Complete trade history with timestamps
- **Status Updates**: Hourly summaries and periodic balance updates
- **Background Operation**: Runs 24/7 with logging

## 📋 Prerequisites

- Python 3.10+
- Polymarket account (Magic Link or wallet-based)
- OpenRouter API key (for AI models)
- Telegram bot token (optional, for notifications)
- IPRoyal residential proxy account (for live trading from cloud servers)

## 🛠️ Installation

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/polymarket-bot.git
cd polymarket-bot
```

### 2. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment
Create a `.env` file in the project root:

```env
# Polymarket Credentials
POLYMARKET_PRIVATE_KEY=0x...your_private_key_here
POLYMARKET_FUNDER_ADDRESS=0x...your_profile_wallet_address

# OpenRouter API (for AI signals)
OPENROUTER_API_KEY=sk-or-v1-...

# Telegram Notifications (optional)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# IPRoyal Proxy (for live trading from cloud)
# Configured in src/utils/vpn_helper.py
```

### 4. Get Your Polymarket Credentials

**Private Key:**
1. Go to Polymarket → Profile → Export Private Key
2. Follow the export process (Magic Link sign-in required)
3. Copy the private key (starts with `0x`)

**Funder Address (Profile Wallet):**
1. Go to your Polymarket profile page
2. Check the URL: `https://polymarket.com/profile/0x...`
3. The `0x...` address in the URL is your funder address
4. **Important**: This is different from your deposit address!

## 🎯 Quick Start

### Paper Trading (Test Mode)
```bash
python -m src.trading.live_trader --mode paper --ai --hours 1
```

### Live Trading
```bash
python -m src.trading.live_trader --mode live --ai --hours 8
```

### Options
- `--mode {paper,live}`: Trading mode (default: paper)
- `--ai`: Use AI mode (Sonnet → Opus), otherwise rule-based
- `--hours N`: Duration in hours (default: 1)
- `--interval {15,30}`: Trading interval in minutes (default: 15)

## 🪟 Windows Setup

For running on Windows PC (recommended for US users):

1. **Install Python 3.10+** from [python.org](https://python.org)
   - Check "Add Python to PATH" during installation

2. **Install Mullvad VPN** (or your preferred VPN)
   - Connect to a non-US server (UK, Canada, etc.)

3. **Run Setup Script**
   ```cmd
   cd windows_setup
   setup.bat
   ```

4. **Configure `.env`** (copy from `.env.example`)

5. **Test Connection**
   ```cmd
   test_connection.bat
   ```

6. **Start Trading**
   ```cmd
   run_bot.bat      # Paper trading
   run_live.bat      # Live trading (requires confirmation)
   ```

## 🔧 Configuration

### Trading Limits (in `src/trading/live_trader.py`)

```python
class TradingConfig:
    INITIAL_CAPITAL = 100.0          # Starting balance
    MAX_POSITION_PCT = 0.07          # 7% max per trade
    MAX_DAILY_DRAWDOWN_PCT = 0.10   # 10% daily loss limit
    CONSECUTIVE_LOSS_HALT = 3        # Stop after 3 losses
    DAILY_TRADE_LIMIT = 8            # Max trades per day
    MIN_ENTRY_MINUTE = 2             # Don't enter before minute 2
    MAX_ENTRY_MINUTE = 10            # Don't enter after minute 10
```

### Proxy Configuration (in `src/utils/vpn_helper.py`)

For cloud servers, configure IPRoyal residential proxy:

```python
PROXY_HOST = "geo.iproyal.com"
PROXY_PORT = 12321
PROXY_USERNAME = "your_username"
PROXY_PASSWORD = "your_password_country-ca_session-..."
```

## 📊 How It Works

### Signal Generation Flow

1. **Market Discovery**: Finds active BTC 15-minute markets via Polymarket API
2. **Sonnet Pre-Filter**: Quick analysis to determine if worth deeper investigation
3. **Context Building**: Gathers multi-timeframe data, order book, sentiment
4. **Chart Generation**: Creates visual charts (15m, 1h, 4h) with indicators
5. **Opus Analysis**: Deep analysis with full context + visual charts
6. **Decision**: HIGH/MEDIUM confidence → Trade, LOW → Hold

### Trading Execution

1. **Risk Check**: Validates position size, daily limits, loss streaks
2. **Order Creation**: Builds signed order with proper parameters
3. **Order Placement**: Posts to Polymarket CLOB API via residential proxy
4. **Balance Update**: Fetches real balance from Polygon blockchain
5. **Notification**: Sends Telegram alert with trade details

## 📁 Project Structure

```
polymarket-bot/
├── src/
│   ├── trading/
│   │   ├── live_trader.py          # Main trading bot
│   │   ├── ai_consensus_signal.py   # AI signal generation
│   │   ├── context_builder.py       # Market context gathering
│   │   ├── chart_generator.py       # Visual chart creation
│   │   ├── indicators.py            # Technical indicators
│   │   └── signal_generator.py      # Rule-based signals
│   ├── market_finder.py             # Find active markets
│   ├── polymarket_client.py         # API client wrapper
│   └── utils/
│       └── vpn_helper.py            # Proxy/VPN configuration
├── data/
│   ├── charts/                      # Generated chart images
│   ├── live_trades.csv              # Trade history
│   └── signals.csv                  # Signal history
├── logs/                            # Runtime logs
├── windows_setup/                   # Windows installation scripts
├── docs/                            # Documentation
└── run_trader.py                   # Entry point script
```

## 🔍 Monitoring

### View Logs
```bash
tail -f logs/overnight.log
```

### Check Bot Status
```bash
ps aux | grep live_trader
```

### Stop Bot
```bash
kill $(cat bot.pid)
```

### Telegram Notifications

The bot sends notifications for:
- Bot startup/shutdown
- Trade executions (with order ID, size, price)
- Hourly summaries (balance, P&L, trade count)
- Risk halts (consecutive losses, drawdown limits)

## ⚠️ Important Notes

### Account Requirements
- **US Users**: Polymarket blocks US IPs. Use VPN or residential proxy
- **Magic Link Accounts**: Use `signature_type=1` and profile wallet as funder
- **Wallet Accounts**: Use `signature_type=0` and wallet address as funder

### Risk Warnings
- **Start Small**: Test with paper trading first
- **Monitor Closely**: Check Telegram notifications regularly
- **Set Limits**: Adjust risk parameters based on your risk tolerance
- **No Guarantees**: Trading involves substantial risk of loss

### Proxy Requirements
- **Cloud Servers**: Must use residential proxy (IPRoyal, Bright Data, etc.)
- **Local PC**: Can use VPN (Mullvad, etc.) or residential IP
- **Datacenter IPs**: Blocked by Cloudflare (AWS, DigitalOcean, etc.)

## 🐛 Troubleshooting

### "Invalid Signature" Error
- **Fix**: Use profile wallet address (from profile URL), not deposit address
- **Check**: Verify `POLYMARKET_FUNDER_ADDRESS` matches profile URL

### "403 Forbidden" / Cloudflare Block
- **Fix**: Configure residential proxy in `src/utils/vpn_helper.py`
- **Test**: Run `test_connection.bat` (Windows) or check proxy status

### Balance Shows $100 Instead of Real Balance
- **Fix**: Ensure `web3` package is installed: `pip install web3`
- **Check**: Verify Polygon RPC endpoint is accessible

### AI Not Working
- **Check**: OpenRouter API key is set in `.env`
- **Verify**: API key has credits/balance
- **Test**: Check OpenRouter dashboard for usage

## 📚 Documentation

- `docs/prompt-eng.md` - AI prompt engineering strategies
- `docs/indicator-research.md` - Technical indicator research
- `QUICKSTART.md` - Quick setup guide
- `windows_setup/README.txt` - Windows-specific instructions

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is for educational purposes. Use at your own risk.

## 🙏 Acknowledgments

- Polymarket for the prediction market platform
- Anthropic for Claude AI models
- OpenRouter for AI API access
- IPRoyal for residential proxy services

---

**⚠️ Disclaimer**: This bot is for educational purposes only. Trading involves substantial risk of loss. Past performance does not guarantee future results. Use at your own risk.
