# Polymarket BTC Trading Bot - Implementation Plan

**Project:** 15-min BTC Up/Down bot on Polymarket  
**Target Market:** https://polymarket.com/event/btc-updown-15m-1769939100  
**Initial Capital:** $500  
**Data Sources:** CryptoCompare BTC/USD, Polymarket top holders, X sentiment (future)

**Reference:** [ClawdBot 247% overnight success](https://www.coinlive.com/news/clawdbot-autonomous-trading-test-achieved-nearly-250-return-in-just)

---

## Key Lessons from 247% Success Case

- Analyzed 50+ past 15-min contracts for momentum patterns
- Captured real-time X sentiment during trades
- Used RSI + short-term moving averages
- Targeted Asia/Europe volatile sessions
- **Rolling compounding:** gradually increased position after wins
- Self-reviewed operations and optimized

---

## 1. Hard Constraints (Non-Negotiable)

| Rule | Value | Rationale |
|------|-------|-----------|
| Max trade size | 10% of account | Survive losing streaks |
| Max open positions | 2 | Prevent overexposure |
| No-trade zone | Last 5 min of interval | Not enough time |
| Drawdown halt | 10% daily | Pause 4 hours, manual review |
| Max trades/day | 8 | Prevent overtrading |
| Consecutive errors | 3 | Pause 1 hour |
| API withdrawal | DISABLED | Security |

---

## 2. Signal Logic

### Data Inputs (every 15-min cycle)
1. **Price:** CryptoCompare BTC/USD
2. **VWAP:** 15-minute volume-weighted average price
3. **RSI:** 14-period relative strength index
4. **Smart Money:** Top holder direction from Polymarket
5. **Momentum:** 60-second price trend

### Entry Signals

**BUY (bet UP) requires 2+ of 3:**
- Price > 15-min VWAP + 0.15%
- RSI between 50-70
- Top holders net buyers (>60% consensus)

**SELL (bet DOWN) requires 2+ of 3:**
- Price < 15-min VWAP - 0.15%
- RSI between 30-50
- Top holders net sellers (>60% consensus)

**HOLD:** Fewer than 2 signals align

### Confidence Tiers & Position Sizing

| Confidence | Signals Aligned | Position Size |
|------------|-----------------|---------------|
| HIGH | 3 of 3 | 10% of account |
| MEDIUM | 2 of 3 | 5% of account |
| LOW | 0-1 | NO TRADE |

---

## 3. Entry Timing

### Within Each 15-Min Window
- **Minutes 0-2:** Too early, insufficient data — WAIT
- **Minutes 2-10:** Optimal entry zone — TRADE IF SIGNAL
- **Minutes 10-15:** Too late — NO NEW POSITIONS

### Session Awareness (UTC)
| Session | Time (UTC) | Volatility | Strategy |
|---------|------------|------------|----------|
| Asia Open | 00:00-04:00 | HIGH | Standard rules |
| Europe Open | 07:00-10:00 | HIGH | Standard rules |
| US Open | 13:00-16:00 | HIGH | Standard rules |
| Off-hours | Other times | LOW | Require HIGH confidence only |

---

## 4. Position Scaling (Win/Loss Adjustment)

### After Losses
- 3 consecutive losses → reduce to 7% max position
- 5 consecutive losses → reduce to 5% max position
- 10% daily drawdown → STOP trading

### After Wins (Rolling Compounding)
- 3 consecutive wins → increase to 12% max position
- 5 consecutive wins → increase to 15% max position
- Any loss → reset to 10% base

---

## 5. Smart Money Tracking

### Who to Track
- Top 10 holders on current BTC Up/Down market
- Filter: accounts with >$1K position and >60% historical win rate

### Data to Capture
- Position direction (UP vs DOWN)
- Position size (relative to their history)
- Timing (when did they enter?)
- Consensus: % of top holders on each side

### Scraping Strategy
- [ ] Check Polymarket API for holder data
- [ ] If no API: browser automation to scrape "Top Holders" section
- [ ] Cache holder addresses, track across multiple intervals
- [ ] Flag when >60% of smart money aligns

---

## 6. Paper Trading Protocol

### Phase 1: Signal-Only (Today)
- Generate BUY/SELL/HOLD signals every 15 min
- Log to `signals.csv` — NO real trades
- Track what *would have* happened
- Telegram alerts for every signal

### Phase 2: Accuracy Validation
- Run for 24-48 hours
- Require >55% accuracy before live trading
- Review losing signals — why did they fail?

### Phase 3: Small Live ($5-10)
- Only after paper trading validates
- Single position at a time
- Full logging

---

## 7. Self-Review Checkpoints

### Every 10 Trades
- Calculate: win rate, avg win, avg loss, profit factor
- If win rate <50%: tighten entry requirements
- If avg loss > avg win: review exit timing
- Log insights to `review.md`

### Daily Summary
- Total P&L (paper or real)
- Best/worst trades with rationale
- Threshold adjustments made
- Next day plan

---

## 8. Backtest Gate (Before Live)

**Requirement:** Must demonstrate edge on historical data

- Minimum 50 intervals backtested
- Win rate >55%
- Profit factor >1.2 (gross wins / gross losses)
- Max drawdown <15%

If backtest fails → adjust parameters → retest

---

## 9. Failure Modes & Recovery

| Scenario | Trigger | Response |
|----------|---------|----------|
| API timeout | 5s+ latency | Retry 3x, then skip interval |
| Data gap | 30s+ missing | HOLD, alert human |
| Consecutive losses | 5 in a row | Halve position size |
| Drawdown | >10% daily | STOP, 4-hour cooldown |
| Error spike | 3 consecutive | Pause 1 hour |

---

## 10. Tech Stack

```
polymarket-bot/
├── data/
│   ├── btc_prices.csv      # Raw price data (running)
│   ├── signals.csv         # Generated signals
│   ├── trades.csv          # Executed trades
│   └── holders.csv         # Smart money snapshots
├── src/
│   ├── fetcher.py          # Price fetching (done)
│   ├── logger.py           # CSV logging (done)
│   ├── indicators.py       # RSI, VWAP, momentum
│   ├── smart_money.py      # Top holder tracking
│   ├── signal_generator.py # Convergence logic
│   ├── risk_manager.py     # Position sizing
│   └── paper_trader.py     # Paper trading loop
├── main.py                 # Orchestration
└── plan-kimi.md            # This file
```

---

## 11. Today's Goals

- [x] Update plan with win-scaling, timing, confidence tiers
- [ ] Build `indicators.py` (RSI, VWAP, momentum)
- [ ] Research Polymarket API for top holder data
- [ ] Build `smart_money.py` or scraping approach
- [ ] Create `signal_generator.py` with paper trading
- [ ] Start paper trading with Telegram alerts

---

*Philosophy: This is your last $100. Protect it. Let edge compound slowly. No YOLO.*
