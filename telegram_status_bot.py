#!/usr/bin/env python3
"""
telegram_status_bot.py - Telegram bot for checking trading bot status

Responds to /status command with current bot status, balance, trades, etc.
Can run alongside the trading bot.

Usage:
    python telegram_status_bot.py
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path
from datetime import datetime
import csv
from decouple import config
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

PROJECT_ROOT = Path(__file__).parent
BOT_PID_FILE = PROJECT_ROOT / "bot.pid"
LOG_DIR = PROJECT_ROOT / "logs"
TRADES_FILE = PROJECT_ROOT / "data" / "live_trades.csv"

def check_process():
    """Check if bot process is running"""
    if not BOT_PID_FILE.exists():
        return None, False, "No PID file found"
    
    try:
        pid = int(BOT_PID_FILE.read_text().strip())
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "pid,etime,cmd"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                info = lines[1].split()
                uptime = info[1] if len(info) > 1 else 'N/A'
                return pid, True, f"Running (PID: {pid}, Uptime: {uptime})"
        
        return pid, False, "Process not found (may have crashed)"
    except Exception as e:
        return None, False, f"Error: {e}"

def get_recent_logs(lines=10):
    """Get recent log entries"""
    log_files = sorted(LOG_DIR.glob("overnight*.log"), reverse=True)
    if not log_files:
        return "No log files found"
    
    try:
        with open(log_files[0], 'r') as f:
            all_lines = f.readlines()
            recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return ''.join(recent).strip()
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

def format_status_message():
    """Format status message for Telegram"""
    # Process status
    pid, is_running, process_status = check_process()
    status_emoji = "✅" if is_running else "❌"
    
    # Balance
    balance = get_balance()
    if isinstance(balance, float):
        balance_str = f"${balance:.2f} USDC"
    else:
        balance_str = str(balance)
    
    # Recent trades
    trades = get_recent_trades(5)
    trades_text = ""
    if trades:
        for i, trade in enumerate(reversed(trades), 1):
            if "error" in trade:
                trades_text += f"   Error: {trade['error']}\n"
            else:
                timestamp = trade.get('timestamp', 'N/A')
                if timestamp != 'N/A':
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_str = dt.strftime('%H:%M:%S UTC')
                    except:
                        time_str = timestamp[:19]
                else:
                    time_str = 'N/A'
                
                signal = trade.get('signal', 'N/A')
                size = trade.get('size_usd', 'N/A')
                order_id = trade.get('order_id', 'N/A')
                if order_id and order_id != 'N/A' and len(order_id) > 20:
                    order_short = order_id[:20] + "..."
                else:
                    order_short = order_id if order_id != 'N/A' else 'N/A'
                
                trades_text += f"{i}. {time_str} | {signal} | ${size} | `{order_short}`\n"
    else:
        trades_text = "   No trades yet\n"
    
    # Recent log activity
    logs = get_recent_logs(5)
    log_lines = logs.split('\n')[-3:] if logs else []
    recent_activity = '\n'.join(log_lines) if log_lines else "No recent activity"
    
    # Build message
    message = f"""🤖 *TRADING BOT STATUS*

{status_emoji} *Process:* {process_status}

💰 *Balance:* {balance_str}

📈 *Recent Trades:*
{trades_text}

📋 *Recent Activity:*
```
{recent_activity}
```

_Use /help for more commands_"""
    
    return message

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    try:
        message = format_status_message()
        await update.message.reply_text(message, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error getting status: {e}")

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command"""
    try:
        balance = get_balance()
        if isinstance(balance, float):
            message = f"💰 *Current Balance:*\n${balance:.2f} USDC"
        else:
            message = f"❌ Error: {balance}"
        await update.message.reply_text(message, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def trades_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /trades command - show recent trades"""
    try:
        trades = get_recent_trades(10)
        if not trades:
            await update.message.reply_text("📊 No trades yet")
            return
        
        message = "📈 *Recent Trades:*\n\n"
        for i, trade in enumerate(reversed(trades), 1):
            if "error" in trade:
                message += f"Error: {trade['error']}\n"
                continue
            
            timestamp = trade.get('timestamp', 'N/A')
            if timestamp != 'N/A':
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                except:
                    time_str = timestamp[:19]
            else:
                time_str = 'N/A'
            
            signal = trade.get('signal', 'N/A')
            size = trade.get('size_usd', 'N/A')
            confidence = trade.get('confidence', 'N/A')
            order_id = trade.get('order_id', 'N/A')
            
            message += f"*{i}.* {time_str}\n"
            message += f"   Signal: {signal} ({confidence})\n"
            message += f"   Size: ${size}\n"
            if order_id != 'N/A':
                order_short = order_id[:30] + "..." if len(order_id) > 30 else order_id
                message += f"   Order: `{order_short}`\n"
            message += "\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /logs command - show recent logs"""
    try:
        logs = get_recent_logs(20)
        if len(logs) > 4000:  # Telegram message limit
            logs = logs[-4000:]
        
        message = f"📋 *Recent Logs:*\n\n```\n{logs}\n```"
        await update.message.reply_text(message, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """🤖 *Trading Bot Commands:*

/status - Full bot status (process, balance, trades, activity)
/balance - Quick balance check
/trades - Recent trades list
/logs - Recent log output
/help - Show this help message

*Note:* This bot monitors your trading bot. Make sure the main trading bot is running for accurate status."""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    """Start the Telegram status bot"""
    token = config("TELEGRAM_BOT_TOKEN", default=None)
    
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN not set in .env")
        print("Please add your Telegram bot token to .env file")
        sys.exit(1)
    
    print("🤖 Starting Telegram Status Bot...")
    print("Commands: /status, /balance, /trades, /logs, /help")
    print("Press Ctrl+C to stop")
    print()
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("trades", trades_command))
    application.add_handler(CommandHandler("logs", logs_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Start bot
    print("✅ Bot is running! Send /status to your bot to test.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
