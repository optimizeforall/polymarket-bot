#!/usr/bin/env python3
"""
check_status.py - Check trading bot status

Quick status check for the running bot including:
- Process status
- Current balance
- Recent trades
- Recent log output
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import csv

PROJECT_ROOT = Path(__file__).parent
BOT_PID_FILE = PROJECT_ROOT / "bot.pid"
LOG_DIR = PROJECT_ROOT / "logs"
TRADES_FILE = PROJECT_ROOT / "data" / "live_trades.csv"

def format_uptime(etime_str):
    """Format ps etime output to simple hours and minutes only"""
    if etime_str == 'N/A' or not etime_str:
        return 'N/A'
    
    # ps etime format: [[DD-]hh:]mm:ss or mm:ss
    parts = etime_str.split(':')
    
    if len(parts) == 2:
        # mm:ss format - convert to hours and minutes
        minutes = int(parts[0])
        hours = minutes // 60
        mins = minutes % 60
        if hours > 0:
            return f"{hours}h {mins}m"
        else:
            return f"{mins}m"
    elif len(parts) == 3:
        # hh:mm:ss format - just use hours and minutes
        hours, minutes, seconds = parts
        return f"{int(hours)}h {int(minutes)}m"
    elif '-' in etime_str:
        # DD-hh:mm:ss format
        day_part, time_part = etime_str.split('-', 1)
        days = int(day_part)
        time_parts = time_part.split(':')
        if len(time_parts) == 3:
            hours, minutes, seconds = time_parts
            total_hours = (days * 24) + int(hours)
            return f"{total_hours}h {int(minutes)}m"
    return etime_str

def check_process():
    """Check if bot process is running and calculate session uptime"""
    if not BOT_PID_FILE.exists():
        return None, "No PID file found"
    
    try:
        pid = int(BOT_PID_FILE.read_text().strip())
        # Check if process exists and get elapsed time
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "etime="],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            etime = result.stdout.strip()
            if etime:
                uptime_formatted = format_uptime(etime)
                return pid, f"Running (PID: {pid}, Uptime: {uptime_formatted})"
        
        return pid, "Process not found (may have crashed)"
    except Exception as e:
        return None, f"Error: {e}"

def get_recent_logs(lines=20):
    """Get recent log entries"""
    log_files = sorted(LOG_DIR.glob("overnight*.log"), reverse=True)
    if not log_files:
        return "No log files found"
    
    try:
        with open(log_files[0], 'r') as f:
            all_lines = f.readlines()
            recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return ''.join(recent)
    except Exception as e:
        return f"Error reading log: {e}"

def get_recent_trades(count=5):
    """Get recent trades from CSV"""
    if not TRADES_FILE.exists():
        return []
    
    try:
        trades = []
        with open(TRADES_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                trades.append(row)
        
        return trades[-count:] if len(trades) > count else trades
    except Exception as e:
        return [{"error": str(e)}]

def get_balance():
    """Get current balance from blockchain"""
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from decouple import config
        from web3 import Web3
        
        w3 = Web3(Web3.HTTPProvider('https://polygon-rpc.com'))
        USDC_ADDRESS = '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'
        funder = config("POLYMARKET_FUNDER_ADDRESS")
        
        usdc_abi = [{
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        }]
        
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ADDRESS),
            abi=usdc_abi
        )
        balance_wei = contract.functions.balanceOf(
            Web3.to_checksum_address(funder)
        ).call()
        balance_usdc = balance_wei / 1e6
        
        return balance_usdc
    except Exception as e:
        return f"Error: {e}"

def main():
    print("=" * 60)
    print("🤖 POLYMARKET TRADING BOT - STATUS CHECK")
    print("=" * 60)
    print()
    
    # Process status
    print("📊 PROCESS STATUS")
    pid, status = check_process()
    print(f"   {status}")
    print()
    
    # Balance
    print("💰 CURRENT BALANCE")
    balance = get_balance()
    if isinstance(balance, float):
        print(f"   ${balance:.2f} USDC")
    else:
        print(f"   {balance}")
    print()
    
    # Recent trades
    print("📈 RECENT TRADES")
    trades = get_recent_trades(5)
    if trades:
        for i, trade in enumerate(reversed(trades), 1):
            if "error" in trade:
                print(f"   Error: {trade['error']}")
            else:
                timestamp = trade.get('timestamp', 'N/A')
                signal = trade.get('signal', 'N/A')
                size = trade.get('size_usd', 'N/A')
                order_id = trade.get('order_id', 'N/A')
                if order_id and order_id != 'N/A':
                    order_short = order_id[:20] + "..." if len(order_id) > 20 else order_id
                else:
                    order_short = 'N/A'
                
                print(f"   {i}. {timestamp[:19]} | {signal} | ${size} | {order_short}")
    else:
        print("   No trades yet")
    print()
    
    # Recent logs
    print("📋 RECENT LOG OUTPUT (last 15 lines)")
    print("-" * 60)
    logs = get_recent_logs(15)
    print(logs)
    print("-" * 60)
    
    print()
    print("=" * 60)
    print("💡 TIPS")
    print("=" * 60)
    print("• View full logs: tail -f logs/overnight*.log")
    print("• Stop bot: kill $(cat bot.pid)")
    print("• Restart bot: python -m src.trading.live_trader --mode live --ai --hours 8 &")
    print()

if __name__ == "__main__":
    main()
