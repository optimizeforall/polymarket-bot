#!/usr/bin/env python3
"""
run_trader.py - Simple entry point to run the trading bot

This is the main script you'll use to start trading.

QUICK START:
    # Paper trading (no real money) - 1 hour test
    python run_trader.py
    
    # Paper trading overnight (8 hours)
    python run_trader.py --hours 8
    
    # LIVE trading (real money!) - be careful
    python run_trader.py --live --hours 8

TELEGRAM SETUP (optional but recommended):
    1. Open Telegram, search for @BotFather
    2. Send /newbot and follow the prompts
    3. Copy the bot token to .env as TELEGRAM_BOT_TOKEN
    4. Search for @userinfobot, send /start to get your chat ID
    5. Copy your chat ID to .env as TELEGRAM_CHAT_ID
"""

import os
import sys
import argparse
from pathlib import Path

# Ensure we're in the right directory
PROJECT_ROOT = Path(__file__).parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "trading"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "core"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


def check_prerequisites():
    """Check that everything is set up correctly"""
    errors = []
    warnings = []
    
    # Check .env file
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        errors.append("❌ .env file not found - copy .env.example to .env")
    else:
        # Check required keys
        from decouple import config
        
        pk = config("POLYMARKET_PRIVATE_KEY", default=None)
        if not pk:
            errors.append("❌ POLYMARKET_PRIVATE_KEY not set in .env")
        
        tg_token = config("TELEGRAM_BOT_TOKEN", default=None)
        tg_chat = config("TELEGRAM_CHAT_ID", default=None)
        if not tg_token or not tg_chat:
            warnings.append("⚠️ Telegram not configured - you won't get notifications")
            warnings.append("   Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
    
    # Check data file
    data_file = PROJECT_ROOT / "data" / "btc_prices.csv"
    if not data_file.exists():
        errors.append("❌ No price data found - run main.py first to collect data")
        errors.append("   python main.py  (let it run for a few minutes)")
    else:
        # Check if data is recent
        import pandas as pd
        from datetime import datetime, timezone, timedelta
        
        try:
            df = pd.read_csv(data_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            latest = df['timestamp'].max()
            
            # Make latest timezone-aware if it isn't
            if latest.tzinfo is None:
                latest = latest.replace(tzinfo=timezone.utc)
            
            age = datetime.now(timezone.utc) - latest
            if age > timedelta(minutes=5):
                warnings.append(f"⚠️ Price data is {age.total_seconds()/60:.0f} minutes old")
                warnings.append("   Run main.py in another terminal to keep data fresh")
            else:
                print(f"✅ Price data is current ({len(df)} rows, {age.total_seconds():.0f}s old)")
        except Exception as e:
            warnings.append(f"⚠️ Could not check data freshness: {e}")
    
    # Print results
    if errors:
        print("\n🚫 SETUP ERRORS:")
        for e in errors:
            print(f"   {e}")
        return False
    
    if warnings:
        print("\n⚠️ WARNINGS:")
        for w in warnings:
            print(f"   {w}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Polymarket BTC Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_trader.py                    # Paper trade for 1 hour
  python run_trader.py --hours 8          # Paper trade overnight
  python run_trader.py --live             # LIVE trading (real money!)
  python run_trader.py --live --hours 8   # LIVE overnight
  
First time? Run these commands first:
  1. python main.py                       # Start price logger (keep running)
  2. python run_trader.py                 # Start paper trading
        """
    )
    
    parser.add_argument("--live", action="store_true",
                       help="Enable LIVE trading with real money (default: paper)")
    parser.add_argument("--hours", type=float, default=1,
                       help="Duration in hours (default: 1)")
    parser.add_argument("--interval", type=int, choices=[15, 30], default=15,
                       help="Trading interval: 15 or 30 minutes (default: 15)")
    parser.add_argument("--ai", action="store_true",
                       help="Use AI mode (Sonnet 3.5 pre-filter → Opus 4.5 decision)")
    parser.add_argument("--skip-checks", action="store_true",
                       help="Skip prerequisite checks")
    
    args = parser.parse_args()
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║           🤖 POLYMARKET BTC TRADING BOT 🤖                    ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Check prerequisites
    if not args.skip_checks:
        if not check_prerequisites():
            print("\n❌ Fix the errors above before running the bot")
            sys.exit(1)
    
    # Confirm live trading
    if args.live:
        print("\n" + "="*60)
        print("⚠️  WARNING: LIVE TRADING MODE ⚠️")
        print("="*60)
        print("You are about to trade with REAL MONEY.")
        print(f"Duration: {args.hours} hours")
        print("="*60)
        
        confirm = input("\nType 'YES' to confirm: ")
        if confirm != "YES":
            print("Cancelled.")
            sys.exit(0)
    
    # Import and run the bot
    from src.trading.live_trader import LiveTradingBot
    
    paper_mode = not args.live
    use_ai = args.ai
    
    if use_ai:
        print("\n🤖 AI MODE: Sonnet 3.5 pre-filter → Opus 4.5 final decision")
        print("   Cost: ~$0.01-0.02 per signal when Opus is called")
        print("   Sonnet filters out weak signals to save money")
    else:
        print("\n📊 RULE-BASED MODE: Using RSI + VWAP + Momentum")
        print("   Cost: $0 (no AI calls)")
    
    bot = LiveTradingBot(paper_mode=paper_mode, interval_minutes=args.interval, use_ai=use_ai)
    
    print(f"\n🚀 Starting {'PAPER' if paper_mode else 'LIVE'} trading for {args.hours} hours...")
    print("   Press Ctrl+C to stop\n")
    
    bot.run(duration_hours=args.hours)


if __name__ == "__main__":
    main()
