import csv
import os
import time
from datetime import datetime, timedelta
from collections import deque

# Try to enable ANSI colors on Windows
try:
    import sys
    if sys.platform == 'win32':
        # Enable ANSI escape sequences on Windows
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
except:
    pass  # If it fails, colors might still work on modern Windows terminals

# ANSI color codes for terminal output
class Colors:
    GREEN = '\033[92m'  # Bright green
    RED = '\033[91m'    # Bright red
    YELLOW = '\033[93m' # Bright yellow
    BLUE = '\033[94m'   # Bright blue
    CYAN = '\033[96m'   # Bright cyan
    WHITE = '\033[97m'  # Bright white
    BOLD = '\033[1m'    # Bold
    RESET = '\033[0m'   # Reset to default
    UP_ARROW = '^'
    DOWN_ARROW = 'v'
    NEUTRAL = '-'

LOG_FILE = "data/btc_prices.csv"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds between retries

# Keep last N prices in memory for quick checks
price_history = deque(maxlen=100)

# Session ID - same for all entries in a session, increments on new session
_session_id = None
_last_entry_timestamp = None

def _get_session_id(timestamp_str):
    """Get the current session ID, starting a new session if there's a gap.
    
    Session ID is the same for all entries in a single session.
    A new session starts if there's a gap of more than 5 minutes between entries.
    """
    global _session_id, _last_entry_timestamp
    
    if _session_id is None:
        # Initialize from CSV - get the last session ID
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "r", newline="") as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    
                    # Check if header has 'id' column
                    has_id_column = header and len(header) > 0 and header[0].lower() == 'id'
                    
                    last_session_id = 0
                    last_timestamp_str = None
                    
                    for row in reader:
                        if row and len(row) > 0:
                            if has_id_column and len(row) > 1:
                                # New format with ID column
                                try:
                                    row_session_id = int(row[0])
                                    if row_session_id > last_session_id:
                                        last_session_id = row_session_id
                                    if len(row) > 1:
                                        last_timestamp_str = row[1]
                                except (ValueError, IndexError):
                                    pass
                            elif not has_id_column and len(row) > 0:
                                # Old format - use first column as timestamp
                                last_timestamp_str = row[0]
                    
                    _session_id = last_session_id
                    _last_entry_timestamp = last_timestamp_str
            except:
                _session_id = 1
                _last_entry_timestamp = None
        else:
            _session_id = 1
            _last_entry_timestamp = None
    
    # Check if we need to start a new session (gap > 5 minutes)
    if _last_entry_timestamp:
        try:
            # Parse ISO format timestamps (remove 'Z' if present, handle microseconds)
            last_time_str = _last_entry_timestamp.replace('Z', '+00:00')
            current_time_str = timestamp_str.replace('Z', '+00:00')
            
            last_time = datetime.fromisoformat(last_time_str)
            current_time = datetime.fromisoformat(current_time_str)
            
            # Calculate gap in seconds
            gap_seconds = (current_time - last_time).total_seconds()
            
            # If gap is more than 5 minutes, start a new session
            if gap_seconds > 300:  # 5 minutes
                _session_id += 1
        except:
            # If parsing fails, assume same session
            pass
    
    # Update last entry timestamp
    _last_entry_timestamp = timestamp_str
    
    return _session_id

def _get_interval(timestamp_str):
    """Calculate 15-minute interval end time in UTC-5 timezone.
    
    Converts UTC timestamp to UTC-5 and returns the interval end time.
    Example: 3:15 AM UTC-5 → "03:30" (end of 3:00-3:15 interval)
    Example: 3:30 AM UTC-5 → "03:45" (end of 3:15-3:30 interval)
    Example: 3:00 AM UTC-5 → "03:15" (end of 3:00-3:15 interval)
    """
    try:
        # Parse UTC timestamp
        time_str = timestamp_str.replace('Z', '+00:00')
        utc_time = datetime.fromisoformat(time_str)
        
        # Convert to UTC-5 (subtract 5 hours)
        utc_minus_5 = utc_time - timedelta(hours=5)
        
        # Calculate 15-minute interval start, then add 15 minutes for end time
        # For 3:15 AM, it should be in 3:00-3:15 interval (returns 03:30 as end)
        minute = utc_minus_5.minute
        # Floor to nearest 15-minute mark to get interval start
        interval_start_minute = (minute // 15) * 15
        
        # Calculate interval end (start + 15 minutes)
        interval_end_minute = interval_start_minute + 15
        if interval_end_minute >= 60:
            # Handle hour rollover
            interval_end_minute = interval_end_minute - 60
            interval_hour = (utc_minus_5.hour + 1) % 24
        else:
            interval_hour = utc_minus_5.hour
        
        # Format as HH:MM (interval end time)
        interval_str = utc_minus_5.replace(hour=interval_hour, minute=interval_end_minute, second=0, microsecond=0)
        return interval_str.strftime("%H:%M")
    except:
        # Fallback if parsing fails
        return "00:15"

def ensure_headers():
    """Ensure CSV file exists with correct headers."""
    expected_headers = ["id", "interval", "timestamp", "price", "volume_24h", "fetch_latency_ms"]
    
    if not os.path.exists(LOG_FILE):
        # Create new file with headers
        with open(LOG_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(expected_headers)
    else:
        # Check if header is correct, fix if needed
        with open(LOG_FILE, "r", newline="") as f:
            reader = csv.reader(f)
            first_line = next(reader, None)
            if first_line != expected_headers:
                # Read all data
                f.seek(0)
                lines = list(csv.reader(f))
                # Fix header
                lines[0] = expected_headers
                
                # Fix old data rows that don't have interval column
                # Old format: [id, timestamp, price, volume, latency] or [timestamp, price, volume, latency]
                # New format: [id, interval, timestamp, price, volume, latency]
                for i in range(1, len(lines)):
                    if len(lines[i]) > 0:
                        # Check if row is missing interval column
                        if len(lines[i]) == 5 and lines[i][1].startswith('202'):  # Old format without interval
                            # Insert empty interval after id
                            lines[i].insert(1, '')
                        elif len(lines[i]) == 4 and lines[i][0].startswith('202'):  # Very old format without id or interval
                            # Insert empty id and interval
                            lines[i].insert(0, '')
                            lines[i].insert(1, '')
                
                # Write back with fixed headers and data
                with open(LOG_FILE, "w", newline="") as fw:
                    writer = csv.writer(fw)
                    writer.writerows(lines)

def fetch_with_retry(fetch_func):
    """Try multiple times before giving up."""
    # Capture precise timestamp at start of fetch
    fetch_start_time = time.time()
    
    for attempt in range(MAX_RETRIES):
        try:
            start = time.time()
            result = fetch_func()
            latency = (time.time() - start) * 1000  # ms
            
            if result:
                result["latency_ms"] = round(latency, 2)
                # Use precise timestamp from fetch start to ensure uniqueness
                # This ensures timestamps are unique even for rapid successive calls
                result["timestamp"] = datetime.utcfromtimestamp(fetch_start_time).isoformat() + "Z"
                return result
                
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
    
    return None

def log_price(price_data):
    timestamp_str = datetime.utcnow().isoformat() + "Z" if price_data is None else price_data["timestamp"]
    session_id = _get_session_id(timestamp_str)
    interval = _get_interval(timestamp_str)
    
    if price_data is None:
        # Log failure so you know gaps exist
        with open(LOG_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                session_id,
                interval,
                timestamp_str,
                "ERROR", "ERROR", "ERROR"
            ])
        # Extract time-only for display (HH:MM:SS)
        try:
            time_obj = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            time_display = time_obj.strftime("%H:%M:%S")
        except:
            time_display = timestamp_str[11:19] if len(timestamp_str) > 19 else timestamp_str
        print(f"{Colors.RED}[{interval}] [{time_display}] {Colors.BOLD}FETCH FAILED{Colors.RESET}", flush=True)
        return
    
    # Store in memory
    price_history.append(price_data)
    
    # Write to disk
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            session_id,
            interval,
            price_data["timestamp"],
            price_data["price"],
            price_data["volume"],
            price_data.get("latency_ms", "")
        ])
    
    # Console output with colored trend indicator
    # Extract time-only for display (HH:MM:SS) - no date
    try:
        time_obj = datetime.fromisoformat(price_data['timestamp'].replace('Z', '+00:00'))
        time_display = time_obj.strftime("%H:%M:%S")
    except:
        time_display = price_data['timestamp'][11:19] if len(price_data['timestamp']) > 19 else price_data['timestamp']
    
    price_str = f"${price_data['price']:,.2f}"
    volume_str = f"${price_data['volume']:,.0f}" if price_data.get('volume', 0) > 0 else "N/A"
    source_str = price_data.get('source', 'Unknown')
    latency_str = f"{price_data.get('latency_ms', 0):.0f}ms" if price_data.get('latency_ms') else ""
    
    # Determine trend and color using actual timestamp differences
    trend_symbol = ""
    trend_color = ""
    price_change = ""
    
    if len(price_history) >= 2:
        prev_data = list(price_history)[-2]
        prev_price = prev_data["price"]
        prev_timestamp = prev_data["timestamp"]
        curr_price = price_data["price"]
        curr_timestamp = price_data["timestamp"]
        
        # Calculate actual time difference in seconds
        try:
            prev_time_str = prev_timestamp.replace('Z', '+00:00')
            curr_time_str = curr_timestamp.replace('Z', '+00:00')
            prev_time = datetime.fromisoformat(prev_time_str)
            curr_time = datetime.fromisoformat(curr_time_str)
            time_diff_seconds = (curr_time - prev_time).total_seconds()
        except:
            # Fallback to assuming 1 second if parsing fails
            time_diff_seconds = 1.0
        
        # Calculate price change using actual time difference (not assumed intervals)
        # This is critical for accurate RSI and other time-sensitive indicators
        price_change_abs = curr_price - prev_price
        price_change_pct = (price_change_abs / prev_price) * 100 if prev_price > 0 else 0
        
        # Calculate rate of change per second (for time-sensitive indicators like RSI)
        # Uses actual timestamp difference, not assumed 1-second intervals
        price_change_per_second = price_change_abs / time_diff_seconds if time_diff_seconds > 0 else 0
        
        # Store time difference in price_data for use in indicators
        price_data["time_diff_seconds"] = time_diff_seconds
        price_data["price_change_per_second"] = price_change_per_second
        
        if curr_price > prev_price:
            trend_symbol = Colors.UP_ARROW
            trend_color = Colors.GREEN
            price_change = f"+${price_change_abs:,.2f} (+{price_change_pct:.2f}%)"
        elif curr_price < prev_price:
            trend_symbol = Colors.DOWN_ARROW
            trend_color = Colors.RED
            price_change = f"${price_change_abs:,.2f} ({price_change_pct:.2f}%)"
        else:
            trend_symbol = Colors.NEUTRAL
            trend_color = Colors.WHITE
            price_change = "$0.00 (0.00%)"
    
    # Format output with colors - show interval and time at beginning (no session ID)
    if trend_symbol:
        output = (f"{Colors.CYAN}[{interval}]{Colors.RESET} "
                  f"{Colors.CYAN}[{time_display}]{Colors.RESET} "
                  f"{Colors.BOLD}{Colors.WHITE}{price_str}{Colors.RESET} "
                  f"{trend_color}{trend_symbol}{Colors.RESET} "
                  f"{trend_color}{price_change}{Colors.RESET} | "
                  f"{Colors.BLUE}Vol: {volume_str}{Colors.RESET} | "
                  f"{Colors.YELLOW}{source_str}{Colors.RESET}")
    else:
        # First entry - no trend yet
        output = (f"{Colors.CYAN}[{interval}]{Colors.RESET} "
                  f"{Colors.CYAN}[{time_display}]{Colors.RESET} "
                  f"{Colors.BOLD}{Colors.WHITE}{price_str}{Colors.RESET} | "
                  f"{Colors.BLUE}Vol: {volume_str}{Colors.RESET} | "
                  f"{Colors.YELLOW}{source_str}{Colors.RESET}")
    
    if latency_str:
        output += f" {Colors.WHITE}({latency_str}){Colors.RESET}"
    
    print(output, flush=True)

def get_stats():
    """Return basic stats from memory."""
    if len(price_history) < 2:
        return None
    
    prices = [p["price"] for p in price_history]
    return {
        "count": len(prices),
        "min": min(prices),
        "max": max(prices),
        "range": max(prices) - min(prices),
        "latest": prices[-1]
    }