"""
live_trader.py - Autonomous BTC 15-min/30-min trading bot for Polymarket

This is the MAIN trading bot. It:
1. Monitors BTC price and generates signals
2. Executes real trades on Polymarket
3. Sends Telegram notifications
4. Runs autonomously overnight
5. Respects hard risk limits

Usage:
    python -m src.trading.live_trader --mode paper    # Paper trading (no real money)
    python -m src.trading.live_trader --mode live     # Live trading with real money
    python -m src.trading.live_trader --mode live --hours 8  # Run for 8 hours overnight
"""

import os
import sys
import time
import json
import csv
import asyncio
import argparse
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Tuple
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "trading"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "core"))

from decouple import config
from signal_generator import run_signal_check, format_signal_message

# Try to import AI consensus (optional)
try:
    from ai_consensus_signal import get_consensus_signal, format_consensus_message
    AI_CONSENSUS_AVAILABLE = True
except ImportError:
    AI_CONSENSUS_AVAILABLE = False

# Try to import Polymarket client
try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs, PartialCreateOrderOptions
    POLYMARKET_AVAILABLE = True
except ImportError:
    POLYMARKET_AVAILABLE = False
    print("⚠️ py-clob-client not available - paper trading only")

# Try to import Telegram
try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️ python-telegram-bot not available - no notifications")


# =============================================================================
# CONFIGURATION - HARD LIMITS (DO NOT CHANGE DURING RUNTIME)
# =============================================================================

class TradingConfig:
    """Hard-coded trading limits - these protect your capital"""
    
    # Account settings
    INITIAL_CAPITAL = 100.0  # Starting balance - your actual $100
    
    # Position limits
    MAX_POSITION_PCT = 0.07  # 7% max per trade ($7 on $100)
    MAX_CONCURRENT_POSITIONS = 2
    
    # Risk limits
    MAX_DAILY_DRAWDOWN_PCT = 0.10  # 10% daily loss = stop trading
    CONSECUTIVE_LOSS_HALT = 3  # 3 losses in a row = halt trading
    DAILY_TRADE_LIMIT = 8
    
    # Timing
    SIGNAL_CHECK_INTERVAL = 60  # Check every 60 seconds
    MIN_ENTRY_MINUTE = 2  # Don't enter before minute 2
    MAX_ENTRY_MINUTE = 10  # Don't enter after minute 10 (15-min mode)
    
    # Polymarket
    CHAIN_ID = 137  # Polygon
    HOST = "https://clob.polymarket.com"
    SIGNATURE_TYPE = 1  # Email/Magic wallet signup
    
    # BTC 15-min market (you'll need to update this with current market)
    # Find at: https://polymarket.com/event/btc-updown-15m-*
    BTC_15M_CONDITION_ID = None  # Set dynamically or manually


# =============================================================================
# TELEGRAM NOTIFICATIONS
# =============================================================================

class TelegramNotifier:
    """Send trade alerts to Telegram"""
    
    def __init__(self):
        self.bot = None
        self.chat_id = None
        self.enabled = False
        
        if TELEGRAM_AVAILABLE:
            try:
                token = config("TELEGRAM_BOT_TOKEN", default=None)
                chat_id = config("TELEGRAM_CHAT_ID", default=None)
                
                if token and chat_id:
                    self.bot = Bot(token=token)
                    self.chat_id = chat_id
                    self.enabled = True
                    print(f"✅ Telegram notifications enabled")
                else:
                    print("⚠️ TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in .env")
            except Exception as e:
                print(f"⚠️ Telegram setup failed: {e}")
    
    async def send_async(self, message: str):
        """Send message asynchronously"""
        if not self.enabled:
            return
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
        except TelegramError as e:
            print(f"⚠️ Telegram error: {e}")
    
    def send(self, message: str):
        """Send message (sync wrapper)"""
        if not self.enabled:
            print(f"[TELEGRAM DISABLED] {message[:100]}...")
            return
        try:
            # Always use a fresh event loop in a thread to avoid conflicts
            import threading
            result = {"error": None}
            def run_in_thread():
                try:
                    asyncio.run(self.send_async(message))
                except Exception as e:
                    result["error"] = e
            thread = threading.Thread(target=run_in_thread, daemon=True)
            thread.start()
            thread.join(timeout=10)  # Wait up to 10 seconds
            if result["error"]:
                print(f"⚠️ Telegram error: {result['error']}")
        except Exception as e:
            print(f"⚠️ Telegram send error: {e}")


# =============================================================================
# POLYMARKET TRADING
# =============================================================================

class PolymarketTrader:
    """Execute trades on Polymarket"""
    
    def __init__(self, paper_mode: bool = True):
        self.paper_mode = paper_mode
        self.client = None
        self.balance = TradingConfig.INITIAL_CAPITAL  # Default, will be updated if live mode
        
        if not paper_mode and POLYMARKET_AVAILABLE:
            self._init_client()
            # Fetch real balance after client is initialized
            self.balance = self.get_balance()
    
    def _init_client(self):
        """Initialize Polymarket CLOB client with IPRoyal proxy"""
        try:
            # Patch HTTP client to use residential proxy
            try:
                from src.utils.vpn_helper import patch_polymarket_client, get_proxy_status
                status = get_proxy_status()
                if status['proxy_available']:
                    patch_polymarket_client(use_proxy=True)
                    print(f"🔒 Using IPRoyal proxy ({status.get('proxy_external_ip', 'Canada')})")
            except ImportError:
                print("⚠️ VPN helper not available - using direct connection")
            
            private_key = config("POLYMARKET_PRIVATE_KEY")
            funder = config("POLYMARKET_FUNDER_ADDRESS", default=None)
            
            self.client = ClobClient(
                TradingConfig.HOST,
                key=private_key,
                chain_id=TradingConfig.CHAIN_ID,
                signature_type=TradingConfig.SIGNATURE_TYPE,
                funder=funder
            )
            
            # Set API credentials using derive (works better than create_or_derive)
            self.client.set_api_creds(self.client.derive_api_key())
            print("✅ Polymarket client initialized")
            
        except Exception as e:
            print(f"❌ Polymarket client failed: {e}")
            self.client = None
            self.paper_mode = True
    
    def get_balance(self) -> float:
        """Get current USDC balance from Polygon blockchain"""
        if self.paper_mode or not self.client:
            return self.balance
        
        try:
            # Query USDC balance directly from Polygon blockchain
            from web3 import Web3
            from decouple import config
            
            # Polygon RPC endpoint
            w3 = Web3(Web3.HTTPProvider('https://polygon-rpc.com'))
            
            # USDC contract on Polygon
            USDC_ADDRESS = '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'
            funder = config("POLYMARKET_FUNDER_ADDRESS")
            
            # USDC ABI (just the balanceOf function)
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
            balance_usdc = balance_wei / 1e6  # USDC has 6 decimals
            
            # Update internal balance tracking
            self.balance = balance_usdc
            return balance_usdc
            
        except Exception as e:
            print(f"⚠️ Balance check failed: {e}")
            # Return cached balance if fetch fails
            return self.balance
    
    def place_order(self, token_id: str, side: str, amount: float, price: float = 0.50) -> Dict:
        """
        Place an order on Polymarket.
        
        Args:
            token_id: The market token ID (YES or NO outcome)
            side: 'BUY' or 'SELL'
            amount: Dollar amount to trade
            price: Limit price (0.01 to 0.99)
        
        Returns:
            Order result dict
        """
        result = {
            "success": False,
            "order_id": None,
            "filled": 0,
            "message": "",
            "paper_mode": self.paper_mode
        }
        
        if self.paper_mode:
            # Simulate order
            result["success"] = True
            result["order_id"] = f"PAPER-{int(time.time())}"
            result["filled"] = amount
            result["message"] = f"Paper order: {side} ${amount:.2f} at {price}"
            
            # Update paper balance
            if side == "BUY":
                self.balance -= amount
            else:
                self.balance += amount
            
            return result
        
        if not self.client:
            result["message"] = "Client not initialized"
            return result
        
        try:
            # Calculate size (shares) from dollar amount and price
            size = amount / price
            
            order_args = OrderArgs(
                token_id=token_id,
                price=price,
                size=size,
                side=side,
                expiration=0  # GTC order (no expiration)
            )
            
            # Create signed order with neg_risk=False for standard markets
            signed_order = self.client.create_order(order_args, PartialCreateOrderOptions(neg_risk=False))
            response = self.client.post_order(signed_order)
            
            result["success"] = response.get("success", False)
            result["order_id"] = response.get("orderID")
            result["filled"] = amount
            result["message"] = f"Order placed: {response}"
            
            # Update balance tracking
            if side == "BUY":
                self.balance -= amount
            
        except Exception as e:
            result["message"] = f"Order failed: {e}"
        
        return result


# =============================================================================
# RISK MANAGER
# =============================================================================

class RiskManager:
    """Enforce trading limits and track performance"""
    
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.daily_start_capital = initial_capital
        
        self.trades_today = 0
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.open_positions = 0
        
        self.is_halted = False
        self.halt_reason = ""
        self.halt_until = None
    
    def can_trade(self) -> Tuple[bool, str]:
        """Check if trading is allowed"""
        
        # Check halt status
        if self.is_halted:
            if self.halt_until and datetime.now(timezone.utc) > self.halt_until:
                self.is_halted = False
                self.halt_reason = ""
            else:
                return False, f"Trading halted: {self.halt_reason}"
        
        # Check daily trade limit
        if self.trades_today >= TradingConfig.DAILY_TRADE_LIMIT:
            return False, f"Daily trade limit reached ({self.trades_today})"
        
        # Check concurrent positions
        if self.open_positions >= TradingConfig.MAX_CONCURRENT_POSITIONS:
            return False, f"Max positions open ({self.open_positions})"
        
        # Check drawdown
        drawdown = (self.daily_start_capital - self.current_capital) / self.daily_start_capital
        if drawdown >= TradingConfig.MAX_DAILY_DRAWDOWN_PCT:
            self.halt_trading(f"Daily drawdown limit ({drawdown:.1%})", hours=4)
            return False, self.halt_reason
        
        return True, "OK"
    
    def get_position_size(self, confidence: str) -> float:
        """Get allowed position size based on confidence and risk state"""
        
        base_pct = TradingConfig.MAX_POSITION_PCT  # 7% = $7 on $100
        
        # Reduce size after consecutive losses (more conservative earlier)
        if self.consecutive_losses >= 2:
            base_pct *= 0.5  # 50% size after 2 losses = 3.5% = $3.50
        
        # Confidence adjustment
        if confidence == "HIGH":
            size_pct = base_pct
        elif confidence == "MEDIUM":
            size_pct = base_pct * 0.5  # MEDIUM = 3.5% normally, 1.75% after losses
        else:
            return 0.0
        
        return self.current_capital * size_pct
    
    def record_trade(self, pnl: float):
        """Record trade result"""
        self.trades_today += 1
        self.current_capital += pnl
        
        if pnl > 0:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
        
        # Check for loss streak halt
        if self.consecutive_losses >= TradingConfig.CONSECUTIVE_LOSS_HALT:
            self.halt_trading(f"Consecutive loss streak ({self.consecutive_losses})", hours=1)
    
    def halt_trading(self, reason: str, hours: float = 4):
        """Halt trading for specified duration"""
        self.is_halted = True
        self.halt_reason = reason
        self.halt_until = datetime.now(timezone.utc) + timedelta(hours=hours)
    
    def reset_daily(self):
        """Reset daily counters (call at start of new day)"""
        self.daily_start_capital = self.current_capital
        self.trades_today = 0
    
    def get_status(self) -> Dict:
        """Get current risk status"""
        drawdown = (self.daily_start_capital - self.current_capital) / self.daily_start_capital
        return {
            "capital": self.current_capital,
            "daily_pnl": self.current_capital - self.daily_start_capital,
            "daily_pnl_pct": (self.current_capital - self.daily_start_capital) / self.daily_start_capital * 100,
            "drawdown_pct": drawdown * 100,
            "trades_today": self.trades_today,
            "consecutive_losses": self.consecutive_losses,
            "consecutive_wins": self.consecutive_wins,
            "is_halted": self.is_halted,
            "halt_reason": self.halt_reason
        }


# =============================================================================
# TRADE LOGGER
# =============================================================================

class TradeLogger:
    """Log all trades to CSV"""
    
    def __init__(self, log_dir: str = "data"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.trades_file = self.log_dir / "live_trades.csv"
        self._ensure_headers()
    
    def _ensure_headers(self):
        """Create CSV with headers if it doesn't exist"""
        if not self.trades_file.exists():
            with open(self.trades_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "interval", "signal", "confidence", "direction",
                    "size_usd", "entry_price", "token_id", "order_id",
                    "paper_mode", "balance_after", "reasons"
                ])
    
    def log_trade(self, trade: Dict):
        """Log a trade to CSV"""
        with open(self.trades_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                trade.get("timestamp"),
                trade.get("interval"),
                trade.get("signal"),
                trade.get("confidence"),
                trade.get("direction"),
                trade.get("size_usd"),
                trade.get("entry_price"),
                trade.get("token_id"),
                trade.get("order_id"),
                trade.get("paper_mode"),
                trade.get("balance_after"),
                trade.get("reasons", "")
            ])


# =============================================================================
# MAIN TRADING BOT
# =============================================================================

class LiveTradingBot:
    """Main autonomous trading bot"""
    
    def __init__(self, paper_mode: bool = True, interval_minutes: int = 15, use_ai: bool = False):
        self.paper_mode = paper_mode
        self.interval_minutes = interval_minutes
        self.use_ai = use_ai and AI_CONSENSUS_AVAILABLE
        
        # Initialize components
        self.trader = PolymarketTrader(paper_mode=paper_mode)
        # Use real balance for risk manager (fetched from blockchain in live mode)
        actual_balance = self.trader.get_balance()
        self.risk_manager = RiskManager(actual_balance)
        self.notifier = TelegramNotifier()
        self.logger = TradeLogger()
        
        # State
        self.running = False
        self.last_signal_interval = None
        self.signals_generated = 0
        self.trades_executed = 0
        
        # Token IDs for current market (need to be set)
        self.yes_token_id = None
        self.no_token_id = None
        self.current_market_title = None
        self.current_market_end = None
        self.current_market_slug = None  # For building Polymarket URL
        
        if self.use_ai:
            print("🤖 AI Mode: Sonnet pre-filter → Opus 4.5 final decision")
        else:
            print("📊 Rule-based Mode: RSI + VWAP + Momentum")
    
    def set_market_tokens(self, yes_token: str, no_token: str):
        """Set the token IDs for the current BTC market"""
        self.yes_token_id = yes_token
        self.no_token_id = no_token
        if yes_token and no_token:
            print(f"📊 Market tokens set: YES={yes_token[:20]}... NO={no_token[:20]}...")
    
    def get_ai_signal(self, indicators: Dict) -> Dict:
        """Get signal using AI (Sonnet pre-filter → Opus 4.5 decision)."""
        if not self.use_ai or not AI_CONSENSUS_AVAILABLE:
            return None
        
        # Build market info
        market_info = {
            'title': self.current_market_title or 'BTC Up/Down 15-min',
            'time_until_end_min': self.current_market_end or 10,
            'up_price': 0.50,
            'down_price': 0.50
        }
        
        # Try to get fresh market prices
        try:
            from market_finder import get_current_tradeable_market
            fresh_market = get_current_tradeable_market(min_time_remaining=3, max_time_remaining=15)
            if fresh_market:
                market_info = fresh_market
                self.set_market_tokens(fresh_market['up_token'], fresh_market['down_token'])
        except:
            pass
        
        # Get AI signal (Sonnet → Opus)
        result = get_consensus_signal(indicators, market_info)
        
        # Send Telegram notification for AI decisions
        if self.notifier.enabled:
            from ai_consensus_signal import format_consensus_message
            self.notifier.send(format_consensus_message(
                result, 
                market_info=market_info, 
                indicators=indicators,
                balance=self.trader.balance
            ))
        
        # Convert to standard signal format
        return {
            "timestamp": result.get("timestamp"),
            "signal": result.get("signal", "HOLD"),
            "confidence": result.get("confidence", "LOW"),
            "position_size": result.get("position_size_pct", 0.0),
            "reasons": [result.get("reasoning", "")],
            "indicators": indicators,
            "entry_window": {"open": True, "message": "AI analysis"},
            "prefilter_passed": result.get("prefilter_passed", False),
            "opus_response": result.get("opus_response"),
            "error": result.get("error")
        }
    
    def find_current_market(self) -> bool:
        """
        Try to find the current BTC 15-min market automatically.
        Returns True if found, False otherwise.
        """
        try:
            # Import market finder
            sys.path.insert(0, str(PROJECT_ROOT / "src"))
            from market_finder import get_current_tradeable_market
            
            market = get_current_tradeable_market(min_time_remaining=3, max_time_remaining=12)
            
            if market:
                self.set_market_tokens(market['up_token'], market['down_token'])
                self.current_market_title = market['title']
                self.current_market_end = market['time_until_end_min']
                self.current_market_slug = market.get('slug', '')
                print(f"📊 Found market: {market['title']}")
                print(f"   Ends in: {market['time_until_end_min']:.1f} minutes")
                if self.current_market_slug:
                    print(f"   URL: https://polymarket.com/event/{self.current_market_slug}")
                print(f"   UP price: {market.get('up_price', 'N/A')}")
                print(f"   DOWN price: {market.get('down_price', 'N/A')}")
                return True
            
            print("⚠️ No tradeable market found in optimal window (3-12 min remaining)")
            return False
            
        except Exception as e:
            print(f"⚠️ Could not find market automatically: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _get_current_interval(self) -> datetime:
        """Get the start of the current interval"""
        now = datetime.now(timezone.utc)
        interval = self.interval_minutes
        return now.replace(
            minute=(now.minute // interval) * interval,
            second=0,
            microsecond=0
        )
    
    def _format_trade_notification(self, signal: Dict, order_result: Dict, size: float) -> str:
        """Format trade notification for Telegram"""
        emoji = "🟢" if signal["signal"] == "BUY" else "🔴"
        direction = "UP" if signal["signal"] == "BUY" else "DOWN"
        
        ind = signal.get("indicators", {})
        status = self.risk_manager.get_status()
        
        mode = "📝 PAPER" if self.paper_mode else "💰 LIVE"
        
        # Get BTC price (check both keys)
        btc_price = ind.get('current_price') or ind.get('price', 0)
        rsi = ind.get('rsi_14') or ind.get('rsi', 0)
        
        # Market info
        market_title = self.current_market_title or 'BTC 15-min'
        time_left = self.current_market_end or 'N/A'
        time_str = f"{time_left:.1f} min" if isinstance(time_left, (int, float)) else str(time_left)
        
        # Build market URL
        market_url = ""
        if self.current_market_slug:
            market_url = f"\n🔗 [View Market](https://polymarket.com/event/{self.current_market_slug})"
        
        return f"""⏰ *{market_title}*
💵 BTC: ${btc_price:,.0f} | ⏳ {time_str} left{market_url}

{emoji} *TRADE EXECUTED* | {signal['confidence']} | {mode}

📊 *Trade Details:*
• Direction: {direction}
• Size: ${size:.2f}
• Entry Price: ${btc_price:,.0f}

📈 *Indicators:*
• RSI: {rsi:.1f}
• VWAP: {ind.get('vwap_deviation_pct', 0):+.2f}%
• Momentum: {ind.get('momentum_60s', 0):+.3f}%

💼 *Account:*
• Balance: ${status['capital']:.2f}
• Today P&L: ${status['daily_pnl']:.2f} ({status['daily_pnl_pct']:+.1f}%)
• Trades: {status['trades_today']}/{TradingConfig.DAILY_TRADE_LIMIT}

🔗 Order: {order_result.get('order_id', 'N/A')}"""
    
    def _format_hourly_summary(self) -> str:
        """Format hourly summary for Telegram"""
        status = self.risk_manager.get_status()
        
        return f"""📊 *HOURLY SUMMARY*

💰 Balance: ${status['capital']:.2f}
📈 Today P&L: ${status['daily_pnl']:.2f} ({status['daily_pnl_pct']:+.1f}%)
🔢 Trades: {status['trades_today']}
✅ Win streak: {status['consecutive_wins']}
❌ Loss streak: {status['consecutive_losses']}

⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC"""
    
    def execute_signal(self, signal: Dict) -> bool:
        """Execute a trading signal"""
        
        # Check if we can trade
        can_trade, reason = self.risk_manager.can_trade()
        if not can_trade:
            print(f"⚠️ Cannot trade: {reason}")
            return False
        
        # Only trade on BUY or SELL signals with sufficient confidence
        if signal["signal"] == "HOLD" or signal["confidence"] == "LOW":
            return False
        
        # Get position size
        size = self.risk_manager.get_position_size(signal["confidence"])
        if size < 1.0:  # Minimum $1 trade
            print(f"⚠️ Position size too small: ${size:.2f}")
            return False
        
        # Determine token (YES for BUY/UP, NO for SELL/DOWN)
        if signal["signal"] == "BUY":
            token_id = self.yes_token_id or "YES_TOKEN_PLACEHOLDER"
            direction = "UP"
        else:
            token_id = self.no_token_id or "NO_TOKEN_PLACEHOLDER"
            direction = "DOWN"
        
        # Execute trade
        print(f"\n🚀 Executing {signal['signal']} for ${size:.2f}...")
        order_result = self.trader.place_order(
            token_id=token_id,
            side="BUY",  # We always BUY the outcome we predict
            amount=size,
            price=0.50  # Default price, adjust based on market
        )
        
        if order_result["success"]:
            self.trades_executed += 1
            self.risk_manager.open_positions += 1
            
            # Refresh balance from blockchain (for live mode)
            if not self.paper_mode:
                actual_balance = self.trader.get_balance()
                # Update risk manager's current capital to match real balance
                self.risk_manager.current_capital = actual_balance
            
            # Log trade
            trade_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "interval": self._get_current_interval().isoformat(),
                "signal": signal["signal"],
                "confidence": signal["confidence"],
                "direction": direction,
                "size_usd": size,
                "entry_price": signal.get("indicators", {}).get("price"),
                "token_id": token_id,
                "order_id": order_result["order_id"],
                "paper_mode": self.paper_mode,
                "balance_after": self.trader.balance,
                "reasons": "; ".join(signal.get("reasons", []))
            }
            self.logger.log_trade(trade_data)
            
            # Send notification
            msg = self._format_trade_notification(signal, order_result, size)
            self.notifier.send(msg)
            
            print(f"✅ Trade executed: {order_result['order_id']}")
            return True
        else:
            print(f"❌ Trade failed: {order_result['message']}")
            return False
    
    def run(self, duration_hours: float = 24):
        """Run the trading bot for specified duration"""
        
        mode_str = "PAPER" if self.paper_mode else "LIVE"
        
        # Get actual balance (fetched from blockchain in live mode)
        actual_balance = self.trader.get_balance()
        
        print(f"\n{'='*60}")
        print(f"🤖 POLYMARKET TRADING BOT - {mode_str} MODE")
        print(f"{'='*60}")
        print(f"⏰ Duration: {duration_hours} hours")
        print(f"📊 Interval: {self.interval_minutes} minutes")
        print(f"💰 Starting capital: ${actual_balance:.2f}")
        print(f"📱 Telegram: {'Enabled' if self.notifier.enabled else 'Disabled'}")
        print(f"{'='*60}\n")
        
        # Send startup notification
        brain_mode = "🤖 AI Mode (Sonnet → Opus 4.5)" if self.use_ai else "📊 Rule-based (RSI/VWAP)"
        startup_msg = f"""🚀 *TRADING BOT STARTED*

Mode: {mode_str}
Brain: {brain_mode}
Duration: {duration_hours}h
Interval: {self.interval_minutes}m
Capital: ${actual_balance:.2f}

⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC"""
        self.notifier.send(startup_msg)
        
        self.running = True
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(hours=duration_hours)
        last_hourly_update = start_time
        
        try:
            while self.running and datetime.now(timezone.utc) < end_time:
                now = datetime.now(timezone.utc)
                current_interval = self._get_current_interval()
                minute_in_interval = now.minute % self.interval_minutes
                
                # Generate signal once per interval during optimal window
                if (current_interval != self.last_signal_interval and 
                    TradingConfig.MIN_ENTRY_MINUTE <= minute_in_interval <= TradingConfig.MAX_ENTRY_MINUTE):
                    
                    print(f"\n[{now.strftime('%H:%M:%S')}] Checking signal for {current_interval.strftime('%H:%M')}...")
                    
                    # Find current market first
                    self.find_current_market()
                    
                    # Generate signal (AI or rule-based)
                    if self.use_ai:
                        print("🤖 Using AI (Sonnet → Opus 4.5)...")
                        from indicators import get_current_indicators
                        indicators = get_current_indicators()
                        signal = self.get_ai_signal(indicators)
                        
                        if signal and signal.get("signal") in ["BUY", "SELL"]:
                            print(f"✅ Opus 4.5: {signal['signal']} ({signal['confidence']})")
                            print(f"   {signal.get('reasoning', '')[:100]}")
                        elif signal:
                            print(f"⚪ {signal.get('reasoning', 'No trade')[:100]}")
                    else:
                        signal = run_signal_check(interval_minutes=self.interval_minutes)
                        print(format_signal_message(signal))
                    
                    self.signals_generated += 1
                    
                    # Execute if actionable
                    if signal and signal["signal"] != "HOLD":
                        self.execute_signal(signal)
                    
                    self.last_signal_interval = current_interval
                    
                    # Refresh balance from blockchain periodically (every signal check in live mode)
                    if not self.paper_mode:
                        try:
                            actual_balance = self.trader.get_balance()
                            self.risk_manager.current_capital = actual_balance
                        except Exception as e:
                            print(f"⚠️ Balance refresh failed: {e}")
                    
                    # Status update
                    elapsed = (now - start_time).total_seconds() / 3600
                    remaining = (end_time - now).total_seconds() / 3600
                    status = self.risk_manager.get_status()
                    print(f"\n📊 Signals: {self.signals_generated} | Trades: {self.trades_executed} | "
                          f"Balance: ${status['capital']:.2f} | {elapsed:.1f}h elapsed | {remaining:.1f}h remaining")
                
                # Hourly summary
                if (now - last_hourly_update).total_seconds() >= 3600:
                    self.notifier.send(self._format_hourly_summary())
                    last_hourly_update = now
                
                # Check for halt conditions
                if self.risk_manager.is_halted:
                    print(f"⚠️ Trading halted: {self.risk_manager.halt_reason}")
                    self.notifier.send(f"⚠️ *TRADING HALTED*\n\n{self.risk_manager.halt_reason}")
                
                # Sleep before next check
                time.sleep(TradingConfig.SIGNAL_CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n\n⚠️ Interrupted by user")
        finally:
            self.running = False
            self._shutdown()
    
    def _shutdown(self):
        """Clean shutdown with final summary"""
        status = self.risk_manager.get_status()
        
        summary = f"""🏁 *TRADING SESSION COMPLETE*

📊 *Final Results:*
• Starting: ${TradingConfig.INITIAL_CAPITAL:.2f}
• Ending: ${status['capital']:.2f}
• P&L: ${status['daily_pnl']:.2f} ({status['daily_pnl_pct']:+.1f}%)

📈 *Activity:*
• Signals generated: {self.signals_generated}
• Trades executed: {self.trades_executed}
• Win streak: {status['consecutive_wins']}
• Loss streak: {status['consecutive_losses']}

⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC"""
        
        print(f"\n{'='*60}")
        print(summary.replace('*', '').replace('•', '-'))
        print(f"{'='*60}")
        
        self.notifier.send(summary)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Polymarket BTC Trading Bot")
    parser.add_argument("--mode", choices=["paper", "live"], default="paper",
                       help="Trading mode (default: paper)")
    parser.add_argument("--hours", type=float, default=1,
                       help="Duration in hours (default: 1)")
    parser.add_argument("--interval", type=int, choices=[15, 30], default=15,
                       help="Trading interval in minutes (default: 15)")
    parser.add_argument("--yes-token", type=str, default=None,
                       help="YES outcome token ID")
    parser.add_argument("--no-token", type=str, default=None,
                       help="NO outcome token ID")
    parser.add_argument("--ai", action="store_true",
                       help="Use AI mode (Sonnet → Opus 4.5) instead of rule-based signals")
    parser.add_argument("--no-vpn", action="store_true",
                       help="Disable VPN routing (use default network)")
    
    args = parser.parse_args()
    
    paper_mode = args.mode == "paper"
    
    # Patch Polymarket client to use VPN if available (for live mode)
    if not paper_mode and not args.no_vpn:
        try:
            from src.utils.vpn_helper import patch_polymarket_client, get_vpn_status
            status = get_vpn_status()
            if status['vpn_available']:
                patch_polymarket_client()
                print(f"🔒 VPN active: {status['vpn_external_ip']}")
            else:
                print("⚠️ VPN not available - using default network (may be blocked)")
        except ImportError:
            print("⚠️ VPN helper not available")
    
    # Create and configure bot
    bot = LiveTradingBot(paper_mode=paper_mode, interval_minutes=args.interval, use_ai=args.ai)
    
    # Set market tokens if provided
    if args.yes_token and args.no_token:
        bot.set_market_tokens(args.yes_token, args.no_token)
    
    # Run
    bot.run(duration_hours=args.hours)


if __name__ == "__main__":
    main()
