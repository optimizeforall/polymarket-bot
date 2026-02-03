"""
context_builder.py - Build comprehensive context for AI trading decisions

Gathers all available information to give Opus the fullest picture:
1. Multi-timeframe price data (15m, 4h, 24h, 3d)
2. Order book depth and imbalance from Polymarket
3. Sentiment analysis (news, Fear/Greed)
4. Current Polymarket market prices and implied probabilities
5. Recent trade history for self-reflection

Research shows LOB (Limit Order Book) microstructure is the #1 predictor
for 15-minute price movements. This module makes that data available.
"""

import requests
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List
from pathlib import Path

# Multi-timeframe BTC price data from CoinGecko
COINGECKO_API = "https://api.coingecko.com/api/v3"


def get_btc_price_history() -> Dict:
    """
    Get multi-timeframe BTC price context.
    
    Returns price data across multiple timeframes to understand
    the larger trend context for 15-minute trading decisions.
    """
    result = {
        "current_price": None,
        "price_1h_ago": None,
        "price_4h_ago": None,
        "price_24h_ago": None,
        "price_3d_ago": None,
        "change_1h_pct": None,
        "change_4h_pct": None,
        "change_24h_pct": None,
        "change_3d_pct": None,
        "high_24h": None,
        "low_24h": None,
        "trend_4h": None,
        "trend_24h": None,
        "trend_3d": None,
        "error": None
    }
    
    try:
        # Get current price + 24h stats
        resp = requests.get(
            f"{COINGECKO_API}/simple/price",
            params={
                "ids": "bitcoin",
                "vs_currencies": "usd",
                "include_24hr_high": "true",
                "include_24hr_low": "true",
                "include_24hr_change": "true"
            },
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json().get("bitcoin", {})
        
        result["current_price"] = data.get("usd")
        result["high_24h"] = data.get("usd_24h_high")
        result["low_24h"] = data.get("usd_24h_low")
        result["change_24h_pct"] = data.get("usd_24h_change")
        
        # Get historical prices for multi-timeframe context
        # CoinGecko market_chart gives us hourly data for the past few days
        resp2 = requests.get(
            f"{COINGECKO_API}/coins/bitcoin/market_chart",
            params={
                "vs_currency": "usd",
                "days": "3"  # 3 days of data
            },
            timeout=15
        )
        resp2.raise_for_status()
        prices = resp2.json().get("prices", [])
        
        if prices and len(prices) > 0:
            current = prices[-1][1]  # Most recent price
            
            # Find prices at various timeframes
            now_ms = prices[-1][0]
            
            for ts, price in reversed(prices):
                hours_ago = (now_ms - ts) / (1000 * 3600)
                
                if result["price_1h_ago"] is None and hours_ago >= 1:
                    result["price_1h_ago"] = price
                if result["price_4h_ago"] is None and hours_ago >= 4:
                    result["price_4h_ago"] = price
                if result["price_24h_ago"] is None and hours_ago >= 24:
                    result["price_24h_ago"] = price
                if result["price_3d_ago"] is None and hours_ago >= 72:
                    result["price_3d_ago"] = price
            
            # Calculate percentage changes
            if result["price_1h_ago"]:
                result["change_1h_pct"] = ((current - result["price_1h_ago"]) / result["price_1h_ago"]) * 100
            if result["price_4h_ago"]:
                result["change_4h_pct"] = ((current - result["price_4h_ago"]) / result["price_4h_ago"]) * 100
            if result["price_3d_ago"]:
                result["change_3d_pct"] = ((current - result["price_3d_ago"]) / result["price_3d_ago"]) * 100
            
            # Determine trends
            def get_trend(change):
                if change is None:
                    return "UNKNOWN"
                if change > 1.0:
                    return "STRONG_UP"
                elif change > 0.3:
                    return "UP"
                elif change > -0.3:
                    return "FLAT"
                elif change > -1.0:
                    return "DOWN"
                else:
                    return "STRONG_DOWN"
            
            result["trend_4h"] = get_trend(result["change_4h_pct"])
            result["trend_24h"] = get_trend(result["change_24h_pct"])
            result["trend_3d"] = get_trend(result["change_3d_pct"])
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


def get_polymarket_orderbook(token_id: str) -> Dict:
    """
    Get order book depth from Polymarket.
    
    This is CRITICAL - research shows LOB data is the #1 predictor
    for short-term price movements.
    
    Returns:
        Dict with bids, asks, spread, imbalance, and liquidity metrics
    """
    result = {
        "bid_depth": 0,
        "ask_depth": 0,
        "best_bid": None,
        "best_ask": None,
        "spread": None,
        "spread_pct": None,
        "imbalance": None,  # Positive = more bids (bullish), Negative = more asks
        "liquidity_score": None,  # 0-100, higher = more liquid
        "top_bids": [],
        "top_asks": [],
        "error": None
    }
    
    try:
        resp = requests.get(
            "https://clob.polymarket.com/book",
            params={"token_id": token_id},
            timeout=10
        )
        resp.raise_for_status()
        book = resp.json()
        
        bids = book.get("bids", [])
        asks = book.get("asks", [])
        
        # Calculate depth (total volume on each side)
        bid_depth = sum(float(b.get("size", 0)) for b in bids)
        ask_depth = sum(float(a.get("size", 0)) for a in asks)
        
        result["bid_depth"] = round(bid_depth, 2)
        result["ask_depth"] = round(ask_depth, 2)
        
        # Best bid/ask and spread
        if bids:
            result["best_bid"] = float(bids[0].get("price", 0))
            result["top_bids"] = [
                {"price": float(b["price"]), "size": float(b["size"])}
                for b in bids[:5]
            ]
        if asks:
            result["best_ask"] = float(asks[0].get("price", 0))
            result["top_asks"] = [
                {"price": float(a["price"]), "size": float(a["size"])}
                for a in asks[:5]
            ]
        
        if result["best_bid"] and result["best_ask"]:
            result["spread"] = result["best_ask"] - result["best_bid"]
            mid_price = (result["best_bid"] + result["best_ask"]) / 2
            result["spread_pct"] = (result["spread"] / mid_price) * 100 if mid_price > 0 else None
        
        # Order imbalance - key signal for short-term direction
        total_depth = bid_depth + ask_depth
        if total_depth > 0:
            # Positive = more buying pressure, Negative = more selling pressure
            result["imbalance"] = round((bid_depth - ask_depth) / total_depth, 3)
        
        # Liquidity score (0-100)
        # Higher is better - more liquid markets have tighter spreads and more depth
        if result["spread_pct"] is not None and total_depth > 0:
            spread_score = max(0, 50 - result["spread_pct"] * 10)  # Lower spread = higher score
            depth_score = min(50, total_depth / 100 * 50)  # More depth = higher score
            result["liquidity_score"] = round(spread_score + depth_score, 1)
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def get_market_context(market_info: Dict) -> Dict:
    """
    Get current Polymarket market prices and implied probabilities.
    
    Args:
        market_info: Dict with up_token, down_token, title, etc.
    
    Returns:
        Dict with market prices, implied probabilities, and order book data
    """
    result = {
        "title": market_info.get("title", "Unknown"),
        "time_remaining_min": market_info.get("time_until_end_min"),
        "up_price": market_info.get("up_price"),
        "down_price": market_info.get("down_price"),
        "implied_up_prob": None,
        "implied_down_prob": None,
        "market_lean": None,  # BULLISH, BEARISH, or NEUTRAL
        "up_orderbook": {},
        "down_orderbook": {},
        "error": None
    }
    
    try:
        # Get current prices from API
        up_token = market_info.get("up_token")
        down_token = market_info.get("down_token")
        
        if up_token:
            resp = requests.get(
                "https://clob.polymarket.com/price",
                params={"token_id": up_token, "side": "buy"},
                timeout=5
            )
            if resp.status_code == 200:
                result["up_price"] = float(resp.json().get("price", 0))
                result["implied_up_prob"] = result["up_price"] * 100
        
        if down_token:
            resp = requests.get(
                "https://clob.polymarket.com/price",
                params={"token_id": down_token, "side": "buy"},
                timeout=5
            )
            if resp.status_code == 200:
                result["down_price"] = float(resp.json().get("price", 0))
                result["implied_down_prob"] = result["down_price"] * 100
        
        # Get order book data for both tokens
        if up_token:
            result["up_orderbook"] = get_polymarket_orderbook(up_token)
        if down_token:
            result["down_orderbook"] = get_polymarket_orderbook(down_token)
        
        # Determine market lean
        if result["implied_up_prob"] and result["implied_down_prob"]:
            diff = result["implied_up_prob"] - result["implied_down_prob"]
            if diff > 10:
                result["market_lean"] = "BULLISH"
            elif diff < -10:
                result["market_lean"] = "BEARISH"
            else:
                result["market_lean"] = "NEUTRAL"
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def get_trade_history(csv_path: str = "data/trades.csv", limit: int = 10) -> List[Dict]:
    """
    Load recent trade history for self-reflection.
    
    Args:
        csv_path: Path to trades CSV
        limit: Number of recent trades to load
    
    Returns:
        List of recent trades with outcomes
    """
    trades = []
    
    try:
        path = Path(csv_path)
        if not path.exists():
            return []
        
        with open(path, 'r') as f:
            reader = csv.DictReader(f)
            all_trades = list(reader)
        
        # Get most recent trades
        recent = all_trades[-limit:] if len(all_trades) > limit else all_trades
        
        for trade in recent:
            trades.append({
                "timestamp": trade.get("timestamp", ""),
                "signal": trade.get("signal", ""),
                "confidence": trade.get("confidence", ""),
                "direction": trade.get("direction", ""),
                "size": trade.get("size_usd", ""),
                "outcome": trade.get("outcome", ""),  # WIN/LOSS
                "pnl": trade.get("pnl", ""),
                "reasons": trade.get("reasons", "")
            })
        
    except Exception as e:
        pass
    
    return trades


def calculate_trade_stats(trades: List[Dict]) -> Dict:
    """Calculate win rate and P&L from trade history."""
    if not trades:
        return {"win_rate": None, "total_pnl": 0, "avg_pnl": 0, "trades": 0}
    
    wins = sum(1 for t in trades if t.get("outcome") == "WIN")
    losses = sum(1 for t in trades if t.get("outcome") == "LOSS")
    total = wins + losses
    
    pnls = []
    for t in trades:
        try:
            pnl = float(t.get("pnl", 0) or 0)
            pnls.append(pnl)
        except:
            pass
    
    return {
        "win_rate": (wins / total * 100) if total > 0 else None,
        "total_pnl": sum(pnls),
        "avg_pnl": sum(pnls) / len(pnls) if pnls else 0,
        "trades": total,
        "wins": wins,
        "losses": losses
    }


def build_full_context(
    indicators: Dict,
    market_info: Dict,
    sentiment: Optional[Dict] = None,
    trade_history_path: str = "data/trades.csv"
) -> Dict:
    """
    Build comprehensive context for AI trading decision.
    
    This is the main function that assembles all available information
    to give Opus the fullest possible picture before making a decision.
    
    Args:
        indicators: Current technical indicators (RSI, VWAP, momentum)
        market_info: Current Polymarket market info
        sentiment: Optional sentiment analysis dict
        trade_history_path: Path to trade history CSV
    
    Returns:
        Dict with all context sections
    """
    context = {
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "technical_indicators": indicators,
        "multi_timeframe": {},
        "market_context": {},
        "sentiment": {},
        "trade_history": {},
        "summary": {}
    }
    
    # 1. Multi-timeframe price context
    context["multi_timeframe"] = get_btc_price_history()
    
    # 2. Polymarket market context with order book
    if market_info:
        context["market_context"] = get_market_context(market_info)
    
    # 3. Sentiment analysis
    if sentiment:
        context["sentiment"] = sentiment
    else:
        # Try to get sentiment if not provided
        try:
            from sentiment_analyzer import get_sentiment_analysis
            context["sentiment"] = get_sentiment_analysis()
        except:
            context["sentiment"] = {"error": "Sentiment analyzer not available"}
    
    # 4. Trade history for self-reflection
    trades = get_trade_history(trade_history_path)
    stats = calculate_trade_stats(trades)
    context["trade_history"] = {
        "recent_trades": trades[-5:],  # Last 5 trades
        "stats": stats
    }
    
    # 5. Build summary - key signals at a glance
    multi = context["multi_timeframe"]
    market = context["market_context"]
    sent = context["sentiment"]
    
    context["summary"] = {
        "btc_price": multi.get("current_price"),
        "trend_4h": multi.get("trend_4h"),
        "trend_24h": multi.get("trend_24h"),
        "trend_3d": multi.get("trend_3d"),
        "rsi": indicators.get("rsi_14"),
        "momentum": indicators.get("momentum_60s"),
        "market_lean": market.get("market_lean"),
        "up_price": market.get("up_price"),
        "down_price": market.get("down_price"),
        "time_remaining": market.get("time_remaining_min"),
        "sentiment_direction": sent.get("aggregate", {}).get("direction") if isinstance(sent.get("aggregate"), dict) else None,
        "fear_greed": sent.get("fear_greed", {}).get("value") if isinstance(sent.get("fear_greed"), dict) else None,
        "recent_win_rate": stats.get("win_rate")
    }
    
    return context


def format_context_for_prompt(context: Dict) -> str:
    """
    Format the full context into a string for the AI prompt.
    
    This creates a structured, readable format that helps Opus
    understand and reason about all the available information.
    """
    lines = []
    
    # Header
    lines.append("=" * 60)
    lines.append("COMPREHENSIVE MARKET CONTEXT")
    lines.append(f"Generated: {context.get('timestamp', 'N/A')}")
    lines.append("=" * 60)
    
    # Multi-timeframe analysis
    multi = context.get("multi_timeframe", {})
    lines.append("\n📊 MULTI-TIMEFRAME BTC ANALYSIS")
    lines.append("-" * 40)
    lines.append(f"Current Price: ${multi.get('current_price', 'N/A'):,.2f}" if multi.get('current_price') else "Current Price: N/A")
    lines.append(f"24h High: ${multi.get('high_24h', 'N/A'):,.2f}" if multi.get('high_24h') else "24h High: N/A")
    lines.append(f"24h Low: ${multi.get('low_24h', 'N/A'):,.2f}" if multi.get('low_24h') else "24h Low: N/A")
    lines.append("")
    lines.append("Price Changes:")
    
    # Handle None values gracefully
    def fmt_change(val, trend=None):
        if val is None:
            return "N/A"
        result = f"{val:+.2f}%"
        if trend:
            result += f" → Trend: {trend}"
        return result
    
    lines.append(f"  • 1 hour:  {fmt_change(multi.get('change_1h_pct'))}")
    lines.append(f"  • 4 hours: {fmt_change(multi.get('change_4h_pct'), multi.get('trend_4h', 'N/A'))}")
    lines.append(f"  • 24 hours: {fmt_change(multi.get('change_24h_pct'), multi.get('trend_24h', 'N/A'))}")
    lines.append(f"  • 3 days: {fmt_change(multi.get('change_3d_pct'), multi.get('trend_3d', 'N/A'))}")
    
    # Technical indicators
    tech = context.get("technical_indicators", {})
    lines.append("\n📈 TECHNICAL INDICATORS (15-min)")
    lines.append("-" * 40)
    lines.append(f"RSI (14): {tech.get('rsi_14', 'N/A')}")
    lines.append(f"VWAP Deviation: {tech.get('vwap_deviation_pct', 'N/A')}%")
    lines.append(f"Momentum (60s): {tech.get('momentum_60s', 'N/A')}%")
    lines.append(f"Short-term Trend: {tech.get('trend', 'N/A')}")
    
    # Market context (Polymarket)
    market = context.get("market_context", {})
    lines.append("\n🎯 POLYMARKET CONTEXT")
    lines.append("-" * 40)
    lines.append(f"Market: {market.get('title', 'N/A')}")
    lines.append(f"Time Remaining: {market.get('time_remaining_min', 'N/A'):.1f} minutes" if market.get('time_remaining_min') else "Time Remaining: N/A")
    lines.append("")
    lines.append("Current Prices (Implied Probability):")
    up_price = market.get('up_price')
    down_price = market.get('down_price')
    implied_up = market.get('implied_up_prob')
    implied_down = market.get('implied_down_prob')
    
    if up_price is not None:
        prob_str = f"{implied_up:.1f}%" if implied_up is not None else "N/A"
        lines.append(f"  • UP:   {up_price:.2f} ({prob_str})")
    if down_price is not None:
        prob_str = f"{implied_down:.1f}%" if implied_down is not None else "N/A"
        lines.append(f"  • DOWN: {down_price:.2f} ({prob_str})")
    lines.append(f"Market Lean: {market.get('market_lean', 'N/A')}")
    
    # Order book analysis (CRITICAL for 15-min predictions)
    up_book = market.get("up_orderbook", {})
    down_book = market.get("down_orderbook", {})
    if up_book or down_book:
        lines.append("\n📚 ORDER BOOK ANALYSIS (Key Predictor)")
        lines.append("-" * 40)
        def safe_fmt(val, fmt_str, default="N/A"):
            if val is None:
                return default
            return fmt_str.format(val)
        
        if up_book and not up_book.get("error"):
            lines.append(f"UP Token Order Book:")
            lines.append(f"  • Bid Depth: ${safe_fmt(up_book.get('bid_depth'), '{:.2f}', '0')}")
            lines.append(f"  • Ask Depth: ${safe_fmt(up_book.get('ask_depth'), '{:.2f}', '0')}")
            lines.append(f"  • Spread: {safe_fmt(up_book.get('spread_pct'), '{:.2f}', 'N/A')}%")
            lines.append(f"  • Imbalance: {safe_fmt(up_book.get('imbalance'), '{:+.3f}', 'N/A')} (+ = buy pressure)")
            lines.append(f"  • Liquidity Score: {safe_fmt(up_book.get('liquidity_score'), '{:.1f}', 'N/A')}/100")
        if down_book and not down_book.get("error"):
            lines.append(f"DOWN Token Order Book:")
            lines.append(f"  • Bid Depth: ${safe_fmt(down_book.get('bid_depth'), '{:.2f}', '0')}")
            lines.append(f"  • Ask Depth: ${safe_fmt(down_book.get('ask_depth'), '{:.2f}', '0')}")
            lines.append(f"  • Spread: {safe_fmt(down_book.get('spread_pct'), '{:.2f}', 'N/A')}%")
            lines.append(f"  • Imbalance: {safe_fmt(down_book.get('imbalance'), '{:+.3f}', 'N/A')}")
    
    # Sentiment
    sent = context.get("sentiment", {})
    if sent and not sent.get("error"):
        lines.append("\n💭 SENTIMENT ANALYSIS")
        lines.append("-" * 40)
        agg = sent.get("aggregate", {})
        fg = sent.get("fear_greed", {})
        if agg:
            agg_score = agg.get('aggregate_score')
            score_str = f"{agg_score:+.3f}" if agg_score is not None else "N/A"
            lines.append(f"Overall: {agg.get('direction', 'N/A')} ({score_str})")
        if fg:
            lines.append(f"Fear & Greed Index: {fg.get('value', 50)} ({fg.get('classification', 'Neutral')})")
        news = sent.get("news", {})
        if news and news.get("sample_headlines"):
            lines.append("Recent Headlines:")
            for h in news["sample_headlines"][:2]:
                lines.append(f"  • {h[:80]}...")
    
    # Trade history
    history = context.get("trade_history", {})
    stats = history.get("stats", {})
    if stats.get("trades"):
        lines.append("\n📜 RECENT PERFORMANCE")
        lines.append("-" * 40)
        lines.append(f"Trades: {stats.get('trades', 0)} | Wins: {stats.get('wins', 0)} | Losses: {stats.get('losses', 0)}")
        if stats.get("win_rate") is not None:
            lines.append(f"Win Rate: {stats['win_rate']:.1f}%")
        total_pnl = stats.get('total_pnl', 0) or 0
        lines.append(f"Total P&L: ${total_pnl:.2f}")
    
    lines.append("\n" + "=" * 60)
    
    return "\n".join(lines)


# Test
if __name__ == "__main__":
    print("Testing context builder...")
    
    # Mock indicators
    indicators = {
        "rsi_14": 65.2,
        "vwap_deviation_pct": 0.15,
        "momentum_60s": 0.08,
        "trend": "UP",
        "current_price": 97500
    }
    
    # Mock market info
    market_info = {
        "title": "Bitcoin ↑ or ↓ | 9:00PM-9:15PM ET",
        "time_until_end_min": 8.5,
        "up_token": "12345",  # Would be real token ID
        "down_token": "67890",
        "up_price": 0.52,
        "down_price": 0.48
    }
    
    print("\nBuilding full context...")
    context = build_full_context(indicators, market_info)
    
    print("\nFormatted context for AI:")
    print(format_context_for_prompt(context))
