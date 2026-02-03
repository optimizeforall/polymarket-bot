"""
market_finder.py - Find current BTC 15-min markets on Polymarket

Uses the Gamma API to find active BTC Up/Down markets.
Reference: https://docs.polymarket.com/quickstart/fetching-data
"""

import requests
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Tuple

# Polymarket APIs
GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"

# Series ID for BTC Up or Down 15m markets (found via /series endpoint)
BTC_UP_DOWN_15M_SERIES_ID = 10192


def get_active_btc_markets(limit: int = 50, interval_type: str = "15m") -> List[Dict]:
    """
    Get all active BTC Up/Down markets.
    
    Args:
        limit: Max events to fetch
        interval_type: "15m" for 15-minute markets (uses series_id)
    
    Returns:
        List of market dicts with token IDs, sorted by end time
    """
    try:
        # Query events by series_id for BTC Up or Down 15m
        # This is the correct way per Polymarket API docs
        resp = requests.get(
            f"{GAMMA_API}/events",
            params={
                "series_id": BTC_UP_DOWN_15M_SERIES_ID,
                "active": "true",
                "closed": "false",
                "limit": limit,
            },
            timeout=30
        )
        resp.raise_for_status()
        events = resp.json()
        
        btc_markets = []
        now = datetime.now(timezone.utc)
        
        for event in events:
            title = event.get('title', '')
            
            end_date_str = event.get('endDate', '')
            try:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                time_until_end = (end_date - now).total_seconds() / 60  # minutes
                
                # Skip markets that have already ended
                if time_until_end <= 0:
                    continue
                    
            except:
                continue
            
            markets = event.get('markets', [])
            if not markets:
                continue
            
            m = markets[0]
            clob_tokens = m.get('clobTokenIds')
            prices = m.get('outcomePrices')
            
            if clob_tokens:
                tokens = json.loads(clob_tokens) if isinstance(clob_tokens, str) else clob_tokens
                price_list = json.loads(prices) if prices and isinstance(prices, str) else prices
                
                if len(tokens) >= 2:
                    # Get REAL-TIME prices from CLOB API (Gamma prices are cached/stale!)
                    up_token = tokens[0]
                    down_token = tokens[1]
                    
                    # Fetch live prices
                    up_price = get_market_price(up_token)
                    down_price = get_market_price(down_token)
                    
                    # Fallback to Gamma prices if CLOB fails
                    if up_price is None:
                        up_price = float(price_list[0]) if price_list else 0.5
                    if down_price is None:
                        down_price = float(price_list[1]) if price_list and len(price_list) > 1 else 0.5
                    
                    btc_markets.append({
                        'title': title,
                        'slug': event.get('slug'),
                        'end_date': end_date_str,
                        'time_until_end_min': time_until_end,
                        'up_token': up_token,
                        'down_token': down_token,
                        'up_price': up_price,
                        'down_price': down_price,
                        'condition_id': m.get('conditionId'),
                        'outcomes': m.get('outcomes'),
                    })
        
        # Sort by end time (soonest first)
        btc_markets.sort(key=lambda x: x['time_until_end_min'])
        
        return btc_markets
        
    except Exception as e:
        print(f"Error fetching markets: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_current_tradeable_market(min_time_remaining: int = 5, max_time_remaining: int = 45) -> Optional[Dict]:
    """
    Get the current BTC market that's optimal for trading.
    
    Args:
        min_time_remaining: Minimum minutes until market ends (avoid last-minute trades)
        max_time_remaining: Maximum minutes until market ends (trade current interval)
    
    Returns:
        Market dict with token IDs, or None
    """
    markets = get_active_btc_markets()
    
    for market in markets:
        time_left = market.get('time_until_end_min', 0)
        
        # Find market in the optimal trading window
        if min_time_remaining <= time_left <= max_time_remaining:
            return market
    
    return None


def get_market_price(token_id: str, side: str = "buy") -> Optional[float]:
    """
    Get current price for a token.
    
    Args:
        token_id: The CLOB token ID
        side: "buy" or "sell"
    
    Returns:
        Price as float, or None
    """
    try:
        resp = requests.get(
            f"{CLOB_API}/price",
            params={"token_id": token_id, "side": side},
            timeout=5
        )
        if resp.status_code == 200:
            return float(resp.json().get('price', 0))
    except:
        pass
    return None


def get_orderbook(token_id: str) -> Optional[Dict]:
    """
    Get orderbook for a token.
    
    Returns:
        Dict with bids and asks
    """
    try:
        resp = requests.get(
            f"{CLOB_API}/book",
            params={"token_id": token_id},
            timeout=5
        )
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None


def print_market_status():
    """Print current market status"""
    print(f"\n{'='*60}")
    print(f"📊 BTC UP/DOWN MARKET STATUS")
    print(f"{'='*60}")
    print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
    
    markets = get_active_btc_markets(limit=500, interval_type="15m")
    
    if not markets:
        print("❌ No active BTC markets found")
        return
    
    print(f"Found {len(markets)} active BTC markets:\n")
    
    for i, market in enumerate(markets[:5], 1):
        time_left = market['time_until_end_min']
        
        # Status indicator
        if time_left < 3:
            status = "🔴 CLOSING"
        elif time_left < 10:
            status = "🟡 ENDING SOON"
        elif time_left < 30:
            status = "🟢 TRADEABLE"
        else:
            status = "⚪ UPCOMING"
        
        print(f"{i}. {status} {market['title']}")
        print(f"   ⏰ Ends in {time_left:.1f} minutes")
        
        # Get prices
        up_price = get_market_price(market['up_token'])
        down_price = get_market_price(market['down_token'])
        
        if up_price is not None:
            print(f"   📈 UP: {up_price:.2f} ({up_price*100:.0f}%)")
        if down_price is not None:
            print(f"   📉 DOWN: {down_price:.2f} ({down_price*100:.0f}%)")
        
        print()
    
    # Highlight best market for trading
    tradeable = get_current_tradeable_market()
    if tradeable:
        print(f"{'='*60}")
        print(f"✅ RECOMMENDED MARKET FOR TRADING:")
        print(f"   {tradeable['title']}")
        print(f"   Time remaining: {tradeable['time_until_end_min']:.1f} min")
        print(f"\n   UP Token:   {tradeable['up_token']}")
        print(f"   DOWN Token: {tradeable['down_token']}")
        print(f"{'='*60}")


def main():
    """Display current market status"""
    print_market_status()


if __name__ == "__main__":
    main()
