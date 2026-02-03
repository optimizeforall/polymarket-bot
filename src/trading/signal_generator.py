"""
signal_generator.py - Trading signal generation for BTC 15-min and 30-min prediction markets

Generates BUY (Up), SELL (Down), or HOLD signals based on:
1. Price vs VWAP deviation
2. RSI levels
3. Momentum direction
4. (Future) Smart money consensus

Supports both 15-minute and 30-minute trading intervals.
"""

import json
import csv
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple

# Try relative import first, then absolute
try:
    from .indicators import get_current_indicators
except ImportError:
    from indicators import get_current_indicators

# Configuration
VWAP_THRESHOLD = 0.15  # % deviation required
RSI_BUY_RANGE = (50, 70)
RSI_SELL_RANGE = (30, 50)
MOMENTUM_THRESHOLD = 0.01  # % per 60 seconds
MIN_DATA_POINTS_15M = 30  # Minimum data points for 15-min mode
MIN_DATA_POINTS_30M = 60  # Minimum data points for 30-min mode

# Timing constraints (within 15-min window)
MIN_ENTRY_MINUTE_15M = 2  # Don't enter before minute 2
MAX_ENTRY_MINUTE_15M = 10  # Don't enter after minute 10

# Timing constraints (within 30-min window)
MIN_ENTRY_MINUTE_30M = 3  # Don't enter before minute 3
MAX_ENTRY_MINUTE_30M = 20  # Don't enter after minute 20


def get_current_interval_minute(interval_minutes: int = 15) -> int:
    """
    Get the current minute within the specified interval.
    
    Args:
        interval_minutes: 15 or 30 for 15-min or 30-min intervals
    
    Returns:
        Current minute within the interval (0 to interval_minutes-1)
    """
    now = datetime.now(timezone.utc)
    return now.minute % interval_minutes


def is_entry_window_open(interval_minutes: int = 15) -> Tuple[bool, str]:
    """
    Check if we're in the valid entry window.
    
    Args:
        interval_minutes: 15 or 30 for 15-min or 30-min intervals
    
    Returns:
        Tuple of (is_open: bool, message: str)
    """
    minute = get_current_interval_minute(interval_minutes)
    
    if interval_minutes == 15:
        min_entry = MIN_ENTRY_MINUTE_15M
        max_entry = MAX_ENTRY_MINUTE_15M
        interval_name = "15-min"
    elif interval_minutes == 30:
        min_entry = MIN_ENTRY_MINUTE_30M
        max_entry = MAX_ENTRY_MINUTE_30M
        interval_name = "30-min"
    else:
        return False, f"Invalid interval: {interval_minutes} (must be 15 or 30)"
    
    if minute < min_entry:
        return False, f"Too early (minute {minute}/{interval_minutes}, wait for minute {min_entry})"
    elif minute > max_entry:
        return False, f"Too late (minute {minute}/{interval_minutes}, cutoff was minute {max_entry})"
    else:
        return True, f"Entry window open ({interval_name}, minute {minute}/{interval_minutes})"


def calculate_confidence(signals_aligned: int, total_signals: int = 3) -> str:
    """
    Calculate confidence level based on signal alignment.
    
    Returns: 'HIGH', 'MEDIUM', or 'LOW'
    """
    if signals_aligned >= 3:
        return 'HIGH'
    elif signals_aligned >= 2:
        return 'MEDIUM'
    else:
        return 'LOW'


def get_position_size(confidence: str, base_size: float = 0.10) -> float:
    """
    Get position size as fraction of account based on confidence.
    
    HIGH: 10% (full)
    MEDIUM: 5% (half)
    LOW: 0% (no trade)
    """
    sizes = {
        'HIGH': base_size,
        'MEDIUM': base_size / 2,
        'LOW': 0.0
    }
    return sizes.get(confidence, 0.0)


def generate_signal(indicators: Dict, smart_money_direction: Optional[str] = None, 
                   interval_minutes: int = 15) -> Dict:
    """
    Generate trading signal from indicators.
    
    Args:
        indicators: Dict from get_current_indicators()
        smart_money_direction: Optional 'UP', 'DOWN', or None
        interval_minutes: 15 or 30 for 15-min or 30-min trading intervals
    
    Returns:
        Dict with signal details
    """
    if interval_minutes not in [15, 30]:
        raise ValueError(f"interval_minutes must be 15 or 30, got {interval_minutes}")
    
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "signal": "HOLD",
        "confidence": "LOW",
        "position_size": 0.0,
        "reasons": [],
        "indicators": {},
        "entry_window": None,
        "error": None,
        "interval_minutes": interval_minutes
    }
    
    # Check for errors
    if "error" in indicators:
        result["error"] = indicators["error"]
        result["reasons"].append(f"Data error: {indicators['error']}")
        return result
    
    # Check data quality
    data_points = indicators.get("data_points", 0)
    min_required = MIN_DATA_POINTS_15M if interval_minutes == 15 else MIN_DATA_POINTS_30M
    if data_points < min_required:
        result["error"] = f"Insufficient data ({data_points} < {min_required} for {interval_minutes}-min mode)"
        result["reasons"].append(result["error"])
        return result
    
    # Check entry window
    window_open, window_msg = is_entry_window_open(interval_minutes)
    result["entry_window"] = {"open": window_open, "message": window_msg}
    
    if not window_open:
        result["reasons"].append(window_msg)
        # Don't return early - still calculate signal for paper trading
    
    # Extract indicators
    price = indicators.get("current_price")
    rsi = indicators.get("rsi_14")
    vwap_dev = indicators.get("vwap_deviation_pct")
    momentum = indicators.get("momentum_60s")
    
    result["indicators"] = {
        "price": price,
        "rsi": rsi,
        "vwap_deviation_pct": vwap_dev,
        "momentum_60s": momentum,
        "data_points": data_points
    }
    
    # Count buy/sell signals
    buy_signals = 0
    sell_signals = 0
    
    # Signal 1: VWAP deviation
    if vwap_dev is not None:
        if vwap_dev > VWAP_THRESHOLD:
            buy_signals += 1
            result["reasons"].append(f"Price above VWAP (+{vwap_dev:.2f}%)")
        elif vwap_dev < -VWAP_THRESHOLD:
            sell_signals += 1
            result["reasons"].append(f"Price below VWAP ({vwap_dev:.2f}%)")
        else:
            result["reasons"].append(f"VWAP neutral ({vwap_dev:.2f}%)")
    
    # Signal 2: RSI
    if rsi is not None:
        if RSI_BUY_RANGE[0] <= rsi <= RSI_BUY_RANGE[1]:
            buy_signals += 1
            result["reasons"].append(f"RSI bullish ({rsi:.1f})")
        elif RSI_SELL_RANGE[0] <= rsi <= RSI_SELL_RANGE[1]:
            sell_signals += 1
            result["reasons"].append(f"RSI bearish ({rsi:.1f})")
        elif rsi > RSI_BUY_RANGE[1]:
            result["reasons"].append(f"RSI overbought ({rsi:.1f}) - caution")
        elif rsi < RSI_SELL_RANGE[0]:
            result["reasons"].append(f"RSI oversold ({rsi:.1f}) - caution")
    
    # Signal 3: Momentum
    if momentum is not None:
        if momentum > MOMENTUM_THRESHOLD:
            buy_signals += 1
            result["reasons"].append(f"Momentum positive (+{momentum:.3f}%)")
        elif momentum < -MOMENTUM_THRESHOLD:
            sell_signals += 1
            result["reasons"].append(f"Momentum negative ({momentum:.3f}%)")
        else:
            result["reasons"].append(f"Momentum flat ({momentum:.3f}%)")
    
    # Signal 4: Smart money (if available)
    if smart_money_direction:
        if smart_money_direction == 'UP':
            buy_signals += 1
            result["reasons"].append("Smart money: UP")
        elif smart_money_direction == 'DOWN':
            sell_signals += 1
            result["reasons"].append("Smart money: DOWN")
    
    # Determine final signal
    total_signals = 3  # VWAP, RSI, Momentum (smart money is bonus)
    
    if buy_signals >= 2 and buy_signals > sell_signals:
        result["signal"] = "BUY"
        result["confidence"] = calculate_confidence(buy_signals, total_signals)
        result["position_size"] = get_position_size(result["confidence"])
    elif sell_signals >= 2 and sell_signals > buy_signals:
        result["signal"] = "SELL"
        result["confidence"] = calculate_confidence(sell_signals, total_signals)
        result["position_size"] = get_position_size(result["confidence"])
    else:
        result["signal"] = "HOLD"
        result["confidence"] = "LOW"
        result["position_size"] = 0.0
        result["reasons"].append(f"Mixed signals: {buy_signals} buy, {sell_signals} sell")
    
    # Override if entry window closed
    if not window_open and result["signal"] != "HOLD":
        result["signal"] = "HOLD"
        result["position_size"] = 0.0
        result["reasons"].append("Signal generated but entry window closed")
    
    return result


def format_signal_message(signal: Dict) -> str:
    """Format signal for Telegram notification."""
    timestamp = signal.get("timestamp", "")[:19].replace("T", " ")
    interval = signal.get("interval_minutes", 15)
    
    emoji_map = {
        "BUY": "🟢",
        "SELL": "🔴", 
        "HOLD": "⚪"
    }
    
    emoji = emoji_map.get(signal["signal"], "❓")
    
    ind = signal.get("indicators", {})
    price = ind.get("price", 0)
    rsi = ind.get("rsi", 0)
    vwap_dev = ind.get("vwap_deviation_pct", 0)
    momentum = ind.get("momentum_60s", 0)
    
    msg = f"""{emoji} **{signal['signal']}** | {signal['confidence']} confidence | {interval}-min mode

📊 **Indicators:**
• Price: ${price:,.2f}
• RSI: {rsi:.1f}
• VWAP: {vwap_dev:+.2f}%
• Momentum: {momentum:+.3f}%

💡 **Reasons:**
{chr(10).join('• ' + r for r in signal.get('reasons', []))}

⏰ {timestamp} UTC"""

    if signal.get("error"):
        msg += f"\n⚠️ Error: {signal['error']}"
    
    return msg


def log_signal(signal: Dict, filepath: str = "data/signals.csv"):
    """Append signal to CSV log."""
    fieldnames = [
        "timestamp", "signal", "confidence", "position_size",
        "price", "rsi", "vwap_deviation_pct", "momentum_60s",
        "data_points", "entry_window_open", "interval_minutes", "reasons"
    ]
    
    ind = signal.get("indicators", {})
    entry = signal.get("entry_window", {})
    
    row = {
        "timestamp": signal.get("timestamp"),
        "signal": signal.get("signal"),
        "confidence": signal.get("confidence"),
        "position_size": signal.get("position_size"),
        "price": ind.get("price"),
        "rsi": ind.get("rsi"),
        "vwap_deviation_pct": ind.get("vwap_deviation_pct"),
        "momentum_60s": ind.get("momentum_60s"),
        "data_points": ind.get("data_points"),
        "entry_window_open": entry.get("open"),
        "interval_minutes": signal.get("interval_minutes", 15),
        "reasons": "; ".join(signal.get("reasons", []))
    }
    
    # Check if file exists and write header if needed
    try:
        with open(filepath, 'r') as f:
            pass
        write_header = False
    except FileNotFoundError:
        write_header = True
    
    with open(filepath, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def run_signal_check(csv_path: str = "data/btc_prices.csv", log_path: str = "data/signals.csv",
                     interval_minutes: int = 15) -> Dict:
    """
    Run a complete signal check.
    
    Args:
        csv_path: Path to BTC price CSV file
        log_path: Path to signal log CSV file
        interval_minutes: 15 or 30 for 15-min or 30-min trading intervals
    
    Returns:
        Signal dict and logs to CSV.
    """
    if interval_minutes not in [15, 30]:
        raise ValueError(f"interval_minutes must be 15 or 30, got {interval_minutes}")
    
    # Get indicators (load data for the appropriate window)
    indicators = get_current_indicators(csv_path, minutes=interval_minutes)
    
    # Generate signal
    signal = generate_signal(indicators, interval_minutes=interval_minutes)
    
    # Log it
    log_signal(signal, log_path)
    
    return signal


# Test
if __name__ == "__main__":
    import sys
    
    # Check for interval argument
    interval = 15
    if len(sys.argv) > 1:
        try:
            interval = int(sys.argv[1])
            if interval not in [15, 30]:
                print(f"Invalid interval: {interval}. Must be 15 or 30. Using default 15.")
                interval = 15
        except ValueError:
            print(f"Invalid interval argument: {sys.argv[1]}. Using default 15.")
            interval = 15
    
    print(f"Running signal check ({interval}-min mode)...")
    signal = run_signal_check(interval_minutes=interval)
    
    print("\n" + "="*50)
    print(format_signal_message(signal))
    print("="*50)
    
    print(f"\nSignal logged to signals.csv")
    print(f"Raw signal data: {json.dumps(signal, indent=2)}")
