# Polymarket BTC Trading Bot

A Python bot for automated BTC prediction market trading on Polymarket, with real-time price logging, technical indicators, and signal generation.

## Project Structure

```
polymarket-bot/
├── main.py                 # Entry point - BTC price logger
├── requirements.txt        # Python dependencies
├── README.md
│
├── src/                    # Source code
│   ├── core/               # Core functionality
│   │   ├── fetcher.py      # Multi-source BTC price fetching
│   │   └── logger.py       # CSV logging with session tracking
│   │
│   ├── trading/            # Trading logic
│   │   ├── indicators.py   # RSI, VWAP, momentum calculations
│   │   ├── signal_generator.py  # Buy/Sell/Hold signal generation
│   │   └── paper_trader.py # Paper trading simulation
│   │
│   └── utils/              # Utility modules
│
├── data/                   # Data files
│   ├── btc_prices.csv      # Historical price data
│   └── signals.csv         # Generated trading signals
│
├── services/               # System services
│   ├── btc-logger.service  # Systemd service for auto-restart
│   └── setup-service.sh    # Service installation script
│
└── docs/                   # Documentation
    ├── plans/              # Project plans
    │   ├── plan.md         # Full implementation guide
    │   ├── plan-kimi.md    # Simplified trading plan
    │   └── todo.md         # Task list
    └── SETUP_PLAN.md       # Setup instructions
```

## Features

- **Multi-source price fetching** - CryptoCompare, Chainlink, Binance, CoinCap, CoinGecko
- **Technical indicators** - RSI, VWAP, momentum
- **Signal generation** - Buy/Sell/Hold based on indicator convergence
- **Paper trading** - Test strategies without real money
- **Auto-restart service** - Systemd service keeps logger running 24/7
- **Session tracking** - Organize data by trading sessions
- **Colored CLI output** - Visual price trends

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the price logger:**
   ```bash
   python main.py
   ```

3. **Install as a service (auto-restart):**
   ```bash
   sudo ./services/setup-service.sh
   ```

## Components

### Price Logger (`main.py`)
Fetches BTC price every 5 seconds and logs to CSV.

### Signal Generator (`src/trading/signal_generator.py`)
Generates trading signals based on:
- Price vs VWAP deviation (>0.15%)
- RSI levels (50-70 for buy, 30-50 for sell)
- Momentum direction

### Paper Trader (`src/trading/paper_trader.py`)
Simulates trades without real money to validate strategies.

## Data Format

CSV columns in `data/btc_prices.csv`:
- `id`: Session ID
- `interval`: 15-minute interval (UTC-5)
- `timestamp`: ISO timestamp (UTC)
- `price`: BTC/USD price
- `volume_24h`: 24h trading volume
- `fetch_latency_ms`: API response time

## Service Management

```bash
# Check status
sudo systemctl status btc-logger

# View logs
sudo journalctl -u btc-logger -f

# Restart
sudo systemctl restart btc-logger

# Stop
sudo systemctl stop btc-logger
```

## API Sources

Price data is fetched from (in order of priority):
1. CryptoCompare (primary - includes volume)
2. Chainlink (on-chain via web3.py)
3. Binance
4. CoinCap
5. CoinGecko

## Requirements

- Python 3.8+
- Ubuntu/Linux for systemd service
- See `requirements.txt` for Python dependencies
