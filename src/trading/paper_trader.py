"""
paper_trader.py - Paper trading loop for signal validation

Runs every 15 minutes, generates signals, and tracks hypothetical performance.
"""

import time
import json
import csv
from datetime import datetime, timezone, timedelta
from signal_generator import run_signal_check, format_signal_message

# Configuration
SIGNAL_INTERVAL_SECONDS = 60  # Check every 60 seconds
LOG_FILE = "data/paper_trades.csv"


def get_next_interval_time() -> datetime:
    """Get the start time of the next 15-minute interval."""
    now = datetime.now(timezone.utc)
    minutes_to_next = 15 - (now.minute % 15)
    if minutes_to_next == 15:
        minutes_to_next = 0
    next_interval = now.replace(second=0, microsecond=0) + timedelta(minutes=minutes_to_next)
    return next_interval


def log_paper_trade(signal: dict, interval_start: str):
    """Log a paper trade to CSV."""
    fieldnames = [
        "interval_start", "signal_time", "signal", "confidence", 
        "position_size_pct", "price", "rsi", "vwap_dev", "momentum",
        "entry_window_open", "outcome", "pnl"
    ]
    
    ind = signal.get("indicators", {})
    entry = signal.get("entry_window", {})
    
    row = {
        "interval_start": interval_start,
        "signal_time": signal.get("timestamp"),
        "signal": signal.get("signal"),
        "confidence": signal.get("confidence"),
        "position_size_pct": signal.get("position_size", 0) * 100,
        "price": ind.get("price"),
        "rsi": ind.get("rsi"),
        "vwap_dev": ind.get("vwap_deviation_pct"),
        "momentum": ind.get("momentum_60s"),
        "entry_window_open": entry.get("open"),
        "outcome": "",  # To be filled when interval resolves
        "pnl": ""       # To be filled when interval resolves
    }
    
    try:
        with open(LOG_FILE, 'r') as f:
            pass
        write_header = False
    except FileNotFoundError:
        write_header = True
    
    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def run_paper_trading_loop(duration_hours: float = 24, notify_callback=None):
    """
    Run paper trading for specified duration.
    
    Args:
        duration_hours: How long to run
        notify_callback: Optional function to call with signal messages
    """
    print(f"\n{'='*60}")
    print(f"🚀 PAPER TRADING STARTED")
    print(f"Duration: {duration_hours} hours")
    print(f"Logging to: {LOG_FILE}")
    print(f"{'='*60}\n")
    
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(hours=duration_hours)
    
    last_signal_interval = None
    signals_generated = 0
    
    while datetime.now(timezone.utc) < end_time:
        now = datetime.now(timezone.utc)
        current_interval = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
        current_minute_in_interval = now.minute % 15
        
        # Generate signal once per interval, during optimal window (minutes 2-10)
        if current_interval != last_signal_interval and 2 <= current_minute_in_interval <= 10:
            print(f"\n[{now.strftime('%H:%M:%S')}] Generating signal for interval {current_interval.strftime('%H:%M')}")
            
            signal = run_signal_check()
            signals_generated += 1
            
            # Format and print
            msg = format_signal_message(signal)
            print(msg)
            
            # Log paper trade
            log_paper_trade(signal, current_interval.isoformat())
            
            # Notify if callback provided
            if notify_callback and signal.get("signal") != "HOLD":
                notify_callback(msg)
            
            last_signal_interval = current_interval
            
            # Status
            elapsed = (now - start_time).total_seconds() / 3600
            remaining = (end_time - now).total_seconds() / 3600
            print(f"\n📊 Status: {signals_generated} signals | {elapsed:.1f}h elapsed | {remaining:.1f}h remaining")
        
        # Sleep before next check
        time.sleep(SIGNAL_INTERVAL_SECONDS)
    
    print(f"\n{'='*60}")
    print(f"✅ PAPER TRADING COMPLETE")
    print(f"Total signals: {signals_generated}")
    print(f"Log file: {LOG_FILE}")
    print(f"{'='*60}")


if __name__ == "__main__":
    # Run for 1 hour as a test (change to 24 for overnight)
    run_paper_trading_loop(duration_hours=1)
