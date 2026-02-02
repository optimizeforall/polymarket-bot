"""
paper_trader.py - Paper trading loop for BTC 15-min signals

Runs continuously, generating signals every interval and logging
what trades WOULD have been made. Tracks accuracy against actual outcomes.
"""

import time
import csv
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List
from signal_generator import run_signal_check, format_signal_message


# Configuration
SIGNAL_INTERVAL_SECONDS = 60  # Check every 60 seconds
LOG_FILE = "paper_trades.csv"
ACCOUNT_BALANCE = 500.0  # Simulated starting balance


def get_current_interval() -> str:
    """Get the current 15-minute interval identifier."""
    now = datetime.now(timezone.utc)
    # Round down to nearest 15 minutes
    interval_start = now.replace(
        minute=(now.minute // 15) * 15,
        second=0,
        microsecond=0
    )
    return interval_start.strftime("%Y-%m-%d %H:%M")


def get_interval_end_time() -> datetime:
    """Get when the current interval ends."""
    now = datetime.now(timezone.utc)
    next_interval = now.replace(
        minute=((now.minute // 15) + 1) * 15 % 60,
        second=0,
        microsecond=0
    )
    if next_interval.minute == 0 and now.minute >= 45:
        next_interval = next_interval + timedelta(hours=1)
    return next_interval


def log_paper_trade(signal: Dict, interval: str, position_size_usd: float):
    """Log a paper trade to CSV."""
    fieldnames = [
        "timestamp", "interval", "signal", "confidence",
        "position_size_pct", "position_size_usd",
        "entry_price", "rsi", "vwap_deviation", "momentum",
        "reasons"
    ]
    
    ind = signal.get("indicators", {})
    
    row = {
        "timestamp": signal.get("timestamp"),
        "interval": interval,
        "signal": signal.get("signal"),
        "confidence": signal.get("confidence"),
        "position_size_pct": signal.get("position_size", 0) * 100,
        "position_size_usd": position_size_usd,
        "entry_price": ind.get("price"),
        "rsi": ind.get("rsi"),
        "vwap_deviation": ind.get("vwap_deviation_pct"),
        "momentum": ind.get("momentum_60s"),
        "reasons": "; ".join(signal.get("reasons", []))
    }
    
    # Check if file exists
    try:
        with open(LOG_FILE, 'r') as f:
            write_header = False
    except FileNotFoundError:
        write_header = True
    
    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def format_paper_trade_alert(signal: Dict, interval: str, trade_size: float) -> str:
    """Format paper trade for Telegram notification."""
    sig = signal.get("signal", "HOLD")
    conf = signal.get("confidence", "LOW")
    ind = signal.get("indicators", {})
    
    emoji_map = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}
    emoji = emoji_map.get(sig, "❓")
    
    direction = "UP" if sig == "BUY" else "DOWN" if sig == "SELL" else "—"
    
    msg = f"""📝 **PAPER TRADE** {emoji}

**Interval:** {interval}
**Signal:** {sig} ({conf})
**Direction:** {direction}
**Paper Size:** ${trade_size:.2f}

**Indicators:**
• Price: ${ind.get('price', 0):,.2f}
• RSI: {ind.get('rsi', 0):.1f}
• VWAP: {ind.get('vwap_deviation_pct', 0):+.2f}%
• Momentum: {ind.get('momentum_60s', 0):+.3f}%

⏰ {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC"""
    
    return msg


def calculate_trade_size(signal: Dict, balance: float) -> float:
    """Calculate trade size in USD."""
    position_pct = signal.get("position_size", 0)
    return balance * position_pct


def run_paper_trading_loop(duration_minutes: int = 60, verbose: bool = True):
    """
    Run paper trading for specified duration.
    
    Args:
        duration_minutes: How long to run (0 = forever)
        verbose: Print to console
    """
    start_time = time.time()
    last_interval = None
    trades_this_session = 0
    
    print(f"\n{'='*60}")
    print(f"🚀 Paper Trading Started")
    print(f"   Duration: {'Continuous' if duration_minutes == 0 else f'{duration_minutes} minutes'}")
    print(f"   Balance: ${ACCOUNT_BALANCE:,.2f}")
    print(f"{'='*60}\n")
    
    try:
        while True:
            # Check duration limit
            if duration_minutes > 0:
                elapsed = (time.time() - start_time) / 60
                if elapsed >= duration_minutes:
                    print(f"\n⏱️ Duration limit reached ({duration_minutes} min)")
                    break
            
            current_interval = get_current_interval()
            
            # Run signal check
            signal = run_signal_check()
            
            if verbose:
                print(f"\n[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Interval: {current_interval}")
                print(f"   Signal: {signal['signal']} ({signal['confidence']})")
            
            # Log trade if signal is not HOLD
            if signal["signal"] != "HOLD":
                trade_size = calculate_trade_size(signal, ACCOUNT_BALANCE)
                log_paper_trade(signal, current_interval, trade_size)
                trades_this_session += 1
                
                if verbose:
                    print(f"   📝 Paper trade logged: {signal['signal']} ${trade_size:.2f}")
                    print(f"   Reasons: {', '.join(signal.get('reasons', [])[:2])}")
            else:
                if verbose:
                    reasons = signal.get("reasons", [])
                    if reasons:
                        print(f"   Reasons: {reasons[0]}")
            
            # Wait for next check
            time.sleep(SIGNAL_INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        print(f"\n\n⏹️ Paper trading stopped by user")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Session Summary")
    print(f"   Trades logged: {trades_this_session}")
    print(f"   Duration: {(time.time() - start_time) / 60:.1f} minutes")
    print(f"{'='*60}")
    
    return trades_this_session


def get_paper_trading_stats() -> Dict:
    """Get statistics from paper trading log."""
    try:
        with open(LOG_FILE, 'r') as f:
            reader = csv.DictReader(f)
            trades = list(reader)
    except FileNotFoundError:
        return {"error": "No paper trades logged yet"}
    
    if not trades:
        return {"total_trades": 0}
    
    buys = sum(1 for t in trades if t.get("signal") == "BUY")
    sells = sum(1 for t in trades if t.get("signal") == "SELL")
    total_size = sum(float(t.get("position_size_usd", 0)) for t in trades)
    
    high_conf = sum(1 for t in trades if t.get("confidence") == "HIGH")
    med_conf = sum(1 for t in trades if t.get("confidence") == "MEDIUM")
    
    return {
        "total_trades": len(trades),
        "buys": buys,
        "sells": sells,
        "high_confidence": high_conf,
        "medium_confidence": med_conf,
        "total_paper_size": total_size,
        "first_trade": trades[0].get("timestamp") if trades else None,
        "last_trade": trades[-1].get("timestamp") if trades else None
    }


# Single signal check for external use
def check_and_report() -> str:
    """Run single signal check and return formatted message."""
    signal = run_signal_check()
    interval = get_current_interval()
    
    if signal["signal"] != "HOLD":
        trade_size = calculate_trade_size(signal, ACCOUNT_BALANCE)
        log_paper_trade(signal, interval, trade_size)
        return format_paper_trade_alert(signal, interval, trade_size)
    else:
        return format_signal_message(signal)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "single":
        # Single check mode
        print(check_and_report())
    else:
        # Continuous mode
        run_paper_trading_loop(duration_minutes=0, verbose=True)
