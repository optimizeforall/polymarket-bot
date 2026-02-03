"""
market_finder.py - Module to find active Polymarket markets

Handles fetching market data and identifying the current 15-minute BTC Up/Down market.
Relies on the Polymarket Gamma API.
"""

import requests
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

# Polymarket API endpoints
GAMMA_API_BASE_URL = "https://gamma-api.polymarket.com"

def get_active_btc_15m_market_info() -> Optional[Dict[str, Any]]:
    """
    Find the MOST RECENT active 15-minute BTC Up/Down market.
    
    These markets typically follow a predictable naming pattern or have a tag
    that can be used for filtering. We'll search for "BTC" and "15m", then
    sort by end date or creation date to find the most current one.
    
    Returns:
        A dictionary containing market info (token IDs, slug, etc.) or None.
    """
    print("Searching for active BTC 15m markets via Gamma API...")
    
    # Parameters to find recent, active crypto markets
    # Note: 'search=BTC' might be too broad, need to refine.
    # We are looking for markets like "BTC Up or Down - HH:MM-HH:MM ET"
    # The exact slug or title pattern might need adjustment based on API responses.
    
    # Try to find active markets tagged 'crypto' and sorted by volume (desc)
    try:
        response = requests.get(
            f"{GAMMA_API_BASE_URL}/markets",
            params={
                "active": True,
                "tag": "crypto",
                "limit": 10, # Fetch a few recent ones
                "order": "volume24hr", # Sort by volume, might give recent active ones
                "ascending": False
            },
            timeout=10
        )
        response.raise_for_status()
        markets = response.json()
        
        if not markets or not isinstance(markets, list):
            print("No markets found or invalid response from Gamma API.")
            return None
            
        # Iterate through markets to find the most relevant BTC 15m market
        # We need a way to identify the CURRENT interval's market. Polymarket
        # often uses specific date/time patterns in titles/slugs.
        # For example: "Bitcoin Up or Down - Feb 3, 1:00PM-1:15PM ET"
        
        # Let's try to filter by title/slug containing "Bitcoin" (or "BTC") and "15m"
        # and also check if the market's endDate is in the near future.
        
        now_utc = datetime.now(timezone.utc)
        
        relevant_markets = []
        for market in markets:
            title = market.get("title", "").lower()
            slug = market.get("slug", "").lower()
            end_date_str = market.get("endDate")
            
            if not end_date_str:
                continue
                
            try:
                # Attempt to parse endDate, assuming ISO format often used
                end_date_dt = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            except ValueError:
                continue # Skip if date format is unexpected
            
            # Check if market is active and relevant, and not yet resolved
            if market.get("active") and not market.get("closed"):
                # Look for Bitcoin and 15m in title/slug
                if ("bitcoin" in title or "btc" in title or "bitcoin" in slug or "btc" in slug) and "15m" in title:
                    # Check if the end date is soon, accounting for timezone.
                    # We want the market that will resolve soonest *relative to current time*.
                    # This logic might need fine-tuning. For now, prioritize markets ending today/tomorrow.
                    time_until_end = (end_date_dt - now_utc).total_seconds()
                    
                    # Basic filter: market ends within the next ~2 hours (covers several 15m intervals)
                    if 0 < time_until_end < (2 * 60 * 60): # Between now and 2 hours from now
                        relevant_markets.append((market, time_until_end))
                        
        if not relevant_markets:
            print("No relevant active BTC 15m markets found with current filters.")
            return None
            
        # Sort by time_until_end to get the market that resolves soonest
        relevant_markets.sort(key=lambda item: item[1])
        
        most_relevant_market, _ = relevant_markets[0]
        
        print(f"Found potential market: {most_relevant_market.get('title')} (Slug: {most_relevant_market.get('slug')})")
        
        # Extract token IDs for YES and NO outcomes.
        # This requires knowing which outcome corresponds to YES/NO.
        # The outcomePrices array often aligns with the outcomes array: price[0] for outcome[0].
        # We need to inspect the structure for 'YES' and 'NO'.
        # Let's assume outcomes are usually ["Yes", "No"] or similar.
        
        outcomes = json.loads(most_relevant_market.get("outcomes", "[]"))
        outcome_prices = json.loads(most_relevant_market.get("outcomePrices", "[]"))
        
        yes_token_id = None
        no_token_id = None
        
        if len(outcomes) == 2 and len(outcome_prices) == 2:
            if outcomes[0].lower() == "yes":
                yes_token_id = most_relevant_market.get("clobTokenIds", "[]").split(',')[0].strip('[]"\' ')
                no_token_id = most_relevant_market.get("clobTokenIds", "[]").split(',')[1].strip('[]"\' ')
            elif outcomes[1].lower() == "yes": # If 'No' is first
                yes_token_id = most_relevant_market.get("clobTokenIds", "[]").split(',')[1].strip('[]"\' ')
                no_token_id = most_relevant_market.get("clobTokenIds", "[]").split(',')[0].strip('[]"\' ')
        
        if yes_token_id and no_token_id:
            return {
                "title": most_relevant_market.get("title"),
                "slug": most_relevant_market.get("slug"),
                "yes_token_id": yes_token_id,
                "no_token_id": no_token_id,
                "end_time": end_date_dt,
                "volume": most_relevant_market.get("volume")
            }
        else:
            print("Could not extract YES/NO token IDs from market data.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching markets from Gamma API: {e}")
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON response from Gamma API.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


# --- Test ---
if __name__ == "__main__":
    print("Testing market finder...")
    
    # Mocking the current time to simulate a mid-interval time
    # In a real run, datetime.now(timezone.utc) is used.
    mock_now = datetime(2026, 2, 3, 0, 5, 0, tzinfo=timezone.utc) # Simulate 00:05 UTC
    
    # We need to be careful with mocking datetime.now in tests
    # For a simple script test, just calling the function is fine.
    
    market_info = get_active_btc_15m_market_info()
    
    if market_info:
        print("\nFound active Bitcoin 15m market:")
        print(f"  Title: {market_info.get('title')}")
        print(f"  Slug: {market_info.get('slug')}")
        print(f"  YES Token ID: {market_info.get('yes_token_id')}")
        print(f"  NO Token ID: {market_info.get('no_token_id')}")
        print(f"  Ends at: {market_info.get('end_time')}")
        print(f"  Volume: {market_info.get('volume')}")
    else:
        print("Could not find an active BTC 15m market.")
