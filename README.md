# Polymarket BTC Price Logger

A Python bot that logs Bitcoin (BTC) price data to CSV with support for multiple API sources including Chainlink Data Streams (same as Polymarket uses).

## Features

- Fetches BTC price from multiple APIs with automatic fallback
- Logs price data to CSV with timestamps, volume, and latency
- 15-minute interval tracking in UTC-5 timezone
- Session tracking
- Colored CLI output with price trend indicators
- Real-time price updates with accurate timestamp spacing

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
```bash
# Windows PowerShell
venv\Scripts\Activate.ps1

# Windows CMD
venv\Scripts\activate.bat

# Mac/Linux
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the main script:
```bash
python main.py
```

The bot will:
- Fetch BTC price every second (configurable in `main.py`)
- Log data to `btc_prices.csv`
- Display colored output with price trends
- Continue until stopped with Ctrl+C

## Data Format

CSV columns:
- `id`: Session ID (same for all entries in a session)
- `interval`: 15-minute interval end time in UTC-5 (e.g., "03:30")
- `timestamp`: Full ISO timestamp (UTC)
- `price`: BTC price in USD
- `volume_24h`: 24-hour trading volume in USD
- `fetch_latency_ms`: API response time in milliseconds

## API Sources

The bot tries APIs in this order:
1. CryptoCompare (primary - includes volume)
2. Chainlink (on-chain via web3.py)
3. Binance
4. CoinCap
5. CoinGecko

## Requirements

- Python 3.8+
- See `requirements.txt` for dependencies
