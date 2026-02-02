# Polymarket Trading Bot - Setup Plan

## Research Findings

### Polymarket API Overview

**Three main APIs:**

| API | Base URL | Purpose |
|-----|----------|---------|
| **CLOB API** | `https://clob.polymarket.com` | Trading - orders, prices, orderbooks |
| **Gamma API** | `https://gamma-api.polymarket.com` | Market discovery, metadata, events |
| **Data API** | `https://data-api.polymarket.com` | User positions, activity, history |

**WebSocket endpoints:**
- `wss://ws-subscriptions-clob.polymarket.com/ws/` — Orderbook updates, order status
- `wss://ws-live-data.polymarket.com` — Low-latency crypto prices

---

### What the API Returns

#### CLOB API (Trading)
```
GET /price           → Current price for a token
GET /book            → Orderbook for a token  
GET /midpoint        → Midpoint price
POST /order          → Place an order (auth required)
DELETE /order        → Cancel an order (auth required)
GET /orders          → Your open orders (auth required)
GET /trades          → Your trade history (auth required)
```

#### Gamma API (Market Data)
```
GET /events          → List all events
GET /markets         → List all markets
GET /events/{id}     → Event details with markets
```

**Example market response includes:**
- `clobTokenIds` — Token IDs for YES/NO outcomes (needed for trading)
- `outcomePrices` — Current prices
- `volume24hr`, `liquidity`
- `endDate`, `closed` status

#### Data API (Positions)
```
GET /positions       → Your current positions
```

**Position response includes:**
- `size` — Number of shares
- `avgPrice` — Average entry price
- `currentValue`, `cashPnl`, `percentPnl`
- `realizedPnl`

---

### Authentication Requirements

**To trade, you need:**
1. **Private key** — Ethereum wallet that owns funds on Polymarket
2. **Funder address** — The address holding your USDC (can be same as signing key)
3. **Signature type:**
   - `0` = EOA (MetaMask, hardware wallet)
   - `1` = Email/Magic wallet
   - `2` = Browser wallet proxy

**Python client setup:**
```python
from py_clob_client.client import ClobClient

client = ClobClient(
    "https://clob.polymarket.com",
    key=PRIVATE_KEY,
    chain_id=137,  # Polygon
    signature_type=0,  # or 1 for email wallet
    funder=FUNDER_ADDRESS
)
client.set_api_creds(client.create_or_derive_api_creds())
```

---

### VPN Setup (Mullvad)

**The problem:** Polymarket is geo-restricted in the US. You need a VPN.

**Mullvad split tunneling:** Works by **APP**, not by website/domain.

#### For Your Personal Computer

**Option 1: Dedicated browser (Recommended)**
- Install Firefox specifically for Polymarket
- In Mullvad: Exclude all apps EXCEPT Firefox
- Use Chrome/other browsers for everything else (won't go through VPN)

**Option 2: VPN toggle**
- Turn VPN on only when using Polymarket
- Turn it off for normal browsing

**Steps for Mullvad split tunneling (Windows/macOS):**
1. Open Mullvad app → Settings → Split tunneling
2. Click the + icon next to apps you want to EXCLUDE from VPN
3. Leave Polymarket browser (Firefox) NOT excluded
4. Test: Visit mullvad.net/check in excluded browser → should show your real IP

#### For This Server (Trading Bot)

**Simpler approach:** Route ALL traffic through VPN
- This server is dedicated to Polymarket trading
- No need for split tunneling
- Just configure Mullvad to run always-on

**Setup:**
```bash
# Install Mullvad CLI
wget https://mullvad.net/media/app/MullvadVPN-2024.x_amd64.deb
sudo dpkg -i MullvadVPN-*.deb

# Login and connect
mullvad account login YOUR_ACCOUNT_NUMBER
mullvad relay set location nl  # or any non-US location
mullvad connect
mullvad auto-connect set on
```

---

## File Structure

```
polymarket-bot/
├── config/
│   ├── settings.py           # API keys, thresholds (gitignored)
│   ├── constraints.py        # Hard limits (code-enforced)
│   └── .env                  # Environment variables (gitignored)
├── data/
│   ├── btc_prices.csv        # Price history (exists)
│   ├── signals.csv           # Generated signals
│   ├── trades.csv            # Executed trades
│   └── paper_trades.csv      # Paper trading results
├── src/
│   ├── __init__.py
│   ├── fetcher.py            # Price fetching (exists)
│   ├── logger.py             # CSV logging (exists)
│   ├── indicators.py         # Technical indicators (exists)
│   ├── signal_generator.py   # Signal logic (exists)
│   ├── risk_manager.py       # Position sizing, limits
│   ├── polymarket_client.py  # Polymarket API wrapper
│   ├── market_finder.py      # Find current 15-min BTC markets
│   └── paper_trader.py       # Paper trading loop
├── scripts/
│   ├── run_paper_trading.py  # Start paper trading
│   ├── run_live_trading.py   # Start live trading
│   └── backtest.py           # Historical backtesting
├── logs/
│   └── bot.log
├── main.py                   # Entry point
├── requirements.txt
├── plan.md
├── plan-kimi.md
├── SETUP_PLAN.md             # This file
└── README.md
```

---

## Setup Checklist

### Phase 1: VPN & Account (You do this)
- [ ] Get Polymarket account working via VPN
- [ ] Fund account with USDC on Polygon
- [ ] Export your private key or get API credentials
- [ ] Note your funder/proxy wallet address
- [ ] Test that you can trade manually first

### Phase 2: API Integration (I do this)
- [ ] Install py-clob-client: `pip install py-clob-client`
- [ ] Create `polymarket_client.py` wrapper
- [ ] Create `market_finder.py` to locate current 15-min BTC markets
- [ ] Test read-only operations (get prices, orderbooks)
- [ ] Test authenticated operations (get positions)

### Phase 3: Paper Trading Tonight
- [ ] Run signal generator every 15 minutes
- [ ] Log what we WOULD have traded
- [ ] Compare against actual market outcomes
- [ ] Calculate win rate by morning

### Phase 4: Live Trading (After validation)
- [ ] Prove >55% win rate on paper
- [ ] Start with $5-10 per trade
- [ ] Gradually scale to $50 max

---

## Credentials You'll Need to Provide

1. **Polymarket Private Key** — For signing transactions
2. **Funder Address** — Wallet address holding your USDC
3. **Signature Type** — How you created your Polymarket account:
   - MetaMask/hardware wallet → type 0
   - Email/Google login → type 1
   - Browser wallet → type 2

**Security note:** Store these in `.env` file, never commit to git.

---

## Next Steps

1. **You:** Set up Mullvad on your computer (dedicated browser approach)
2. **You:** Create/fund Polymarket account, get credentials
3. **Me:** Start paper trading loop NOW
4. **Me:** Build `polymarket_client.py` and `market_finder.py`
5. **Tonight:** Collect paper trading data
6. **Tomorrow AM:** Review results, decide on live trading

---

## Questions to Answer

1. How did you create your Polymarket account? (Email, MetaMask, etc.)
2. Do you already have USDC on Polygon, or need to bridge?
3. What non-US country should we connect VPN to? (Netherlands is popular)
