"""
sentiment_analyzer.py - Sentiment analysis for BTC trading signals

Analyzes sentiment from multiple sources:
1. News headlines (CryptoCompare, CoinGecko)
2. Social media mentions (Twitter/X via public APIs)
3. Market fear/greed index
4. On-chain metrics (if available)

Returns sentiment score (-1.0 to +1.0) and direction (BULLISH, BEARISH, NEUTRAL)
"""

import requests
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List, Tuple
import re


# Configuration
SENTIMENT_WEIGHTS = {
    "news": 0.4,
    "social": 0.3,
    "fear_greed": 0.2,
    "on_chain": 0.1
}

FEAR_GREED_THRESHOLDS = {
    "extreme_fear": 25,
    "fear": 45,
    "neutral": 55,
    "greed": 75,
    "extreme_greed": 75
}


def analyze_text_sentiment(text: str) -> float:
    """
    Simple sentiment analysis using keyword matching.
    
    Returns sentiment score from -1.0 (very bearish) to +1.0 (very bullish).
    
    Args:
        text: Text to analyze
    
    Returns:
        Sentiment score (-1.0 to +1.0)
    """
    if not text:
        return 0.0
    
    text_lower = text.lower()
    
    # Bullish keywords (weighted)
    bullish_keywords = {
        "pump": 0.3, "moon": 0.4, "bullish": 0.3, "buy": 0.2,
        "rally": 0.3, "surge": 0.3, "breakout": 0.3, "uptrend": 0.3,
        "support": 0.2, "accumulate": 0.2, "hodl": 0.1, "long": 0.2,
        "green": 0.1, "gains": 0.2, "profit": 0.2, "win": 0.1
    }
    
    # Bearish keywords (weighted)
    bearish_keywords = {
        "dump": 0.3, "crash": 0.4, "bearish": 0.3, "sell": 0.2,
        "drop": 0.3, "plunge": 0.4, "breakdown": 0.3, "downtrend": 0.3,
        "resistance": 0.2, "short": 0.2, "red": 0.1, "loss": 0.2,
        "fear": 0.2, "panic": 0.3, "correction": 0.2, "bear": 0.2
    }
    
    # Count keyword matches
    bullish_score = 0.0
    bearish_score = 0.0
    
    for keyword, weight in bullish_keywords.items():
        count = text_lower.count(keyword)
        bullish_score += count * weight
    
    for keyword, weight in bearish_keywords.items():
        count = text_lower.count(keyword)
        bearish_score += count * weight
    
    # Normalize to -1.0 to +1.0 range
    total_score = bullish_score - bearish_score
    # Cap at reasonable range (prevent extreme scores from single mentions)
    normalized = max(-1.0, min(1.0, total_score / 10.0))
    
    return round(normalized, 3)


def get_news_sentiment(limit: int = 10) -> Dict:
    """
    Fetch recent BTC news and analyze sentiment.
    
    Args:
        limit: Number of news articles to fetch
    
    Returns:
        Dict with sentiment score and sample headlines
    """
    try:
        # Try CryptoCompare news API
        response = requests.get(
            "https://min-api.cryptocompare.com/data/v2/news/?lang=EN&categories=BTC",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("Response") == "Success" and data.get("Data"):
            articles = data["Data"][:limit]
            headlines = [article.get("title", "") for article in articles]
            
            # Analyze sentiment of all headlines
            sentiments = [analyze_text_sentiment(h) for h in headlines]
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
            
            return {
                "score": round(avg_sentiment, 3),
                "source": "CryptoCompare",
                "articles_analyzed": len(headlines),
                "sample_headlines": headlines[:3]
            }
    except Exception as e:
        pass
    
    # Fallback: Try CoinGecko news
    try:
        response = requests.get(
            "https://api.coingecko.com/api/v3/news",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()
        data = response.json()
        
        if data and isinstance(data, list):
            # Filter for BTC-related news
            btc_articles = [
                article for article in data[:limit * 2]
                if "bitcoin" in article.get("title", "").lower() or 
                   "btc" in article.get("title", "").lower()
            ][:limit]
            
            if btc_articles:
                headlines = [article.get("title", "") for article in btc_articles]
                sentiments = [analyze_text_sentiment(h) for h in headlines]
                avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
                
                return {
                    "score": round(avg_sentiment, 3),
                    "source": "CoinGecko",
                    "articles_analyzed": len(headlines),
                    "sample_headlines": headlines[:3]
                }
    except Exception as e:
        pass
    
    return {
        "score": 0.0,
        "source": "none",
        "articles_analyzed": 0,
        "sample_headlines": [],
        "error": "Failed to fetch news"
    }


def get_fear_greed_index() -> Dict:
    """
    Fetch Bitcoin Fear & Greed Index.
    
    Returns:
        Dict with index value (0-100) and sentiment interpretation
    """
    try:
        response = requests.get(
            "https://api.alternative.me/fng/",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("data") and len(data["data"]) > 0:
            latest = data["data"][0]
            value = int(latest.get("value", 50))
            classification = latest.get("value_classification", "Neutral")
            
            # Convert to sentiment score (-1.0 to +1.0)
            # 0-25: Extreme Fear (-1.0 to -0.5)
            # 25-45: Fear (-0.5 to -0.2)
            # 45-55: Neutral (-0.2 to +0.2)
            # 55-75: Greed (+0.2 to +0.5)
            # 75-100: Extreme Greed (+0.5 to +1.0)
            
            if value <= 25:
                sentiment_score = -1.0 + (value / 25) * 0.5
            elif value <= 45:
                sentiment_score = -0.5 + ((value - 25) / 20) * 0.3
            elif value <= 55:
                sentiment_score = -0.2 + ((value - 45) / 10) * 0.4
            elif value <= 75:
                sentiment_score = 0.2 + ((value - 55) / 20) * 0.3
            else:
                sentiment_score = 0.5 + ((value - 75) / 25) * 0.5
            
            return {
                "value": value,
                "classification": classification,
                "sentiment_score": round(sentiment_score, 3),
                "timestamp": latest.get("timestamp", "")
            }
    except Exception as e:
        pass
    
    return {
        "value": 50,
        "classification": "Neutral",
        "sentiment_score": 0.0,
        "error": "Failed to fetch Fear & Greed Index"
    }


def get_social_sentiment() -> Dict:
    """
    Analyze social media sentiment (placeholder - would need Twitter API).
    
    For now, returns neutral sentiment. In production, this would:
    - Query Twitter/X API for BTC-related tweets
    - Analyze sentiment of recent tweets
    - Consider retweet/like ratios
    
    Returns:
        Dict with sentiment score
    """
    # TODO: Implement Twitter/X API integration
    # For now, return neutral
    return {
        "score": 0.0,
        "source": "none",
        "tweets_analyzed": 0,
        "note": "Social sentiment analysis requires Twitter API access"
    }


def get_on_chain_sentiment() -> Dict:
    """
    Analyze on-chain metrics for sentiment (placeholder).
    
    Would analyze:
    - Exchange flows (inflows = bearish, outflows = bullish)
    - Whale movements
    - Active addresses
    - Transaction volume
    
    Returns:
        Dict with sentiment score
    """
    # TODO: Implement on-chain analysis
    # For now, return neutral
    return {
        "score": 0.0,
        "source": "none",
        "note": "On-chain sentiment analysis requires blockchain data APIs"
    }


def calculate_aggregate_sentiment(news: Dict, social: Dict, fear_greed: Dict, 
                                  on_chain: Dict) -> Dict:
    """
    Calculate weighted aggregate sentiment from all sources.
    
    Args:
        news: News sentiment dict
        social: Social sentiment dict
        fear_greed: Fear & Greed Index dict
        on_chain: On-chain sentiment dict
    
    Returns:
        Dict with aggregate sentiment score and direction
    """
    # Get individual scores
    news_score = news.get("score", 0.0)
    social_score = social.get("score", 0.0)
    fear_greed_score = fear_greed.get("sentiment_score", 0.0)
    on_chain_score = on_chain.get("score", 0.0)
    
    # Calculate weighted average
    weights = SENTIMENT_WEIGHTS
    total_weight = sum(weights.values())
    
    aggregate = (
        news_score * weights["news"] +
        social_score * weights["social"] +
        fear_greed_score * weights["fear_greed"] +
        on_chain_score * weights["on_chain"]
    ) / total_weight
    
    # Determine direction
    if aggregate > 0.2:
        direction = "BULLISH"
    elif aggregate < -0.2:
        direction = "BEARISH"
    else:
        direction = "NEUTRAL"
    
    return {
        "aggregate_score": round(aggregate, 3),
        "direction": direction,
        "components": {
            "news": round(news_score, 3),
            "social": round(social_score, 3),
            "fear_greed": round(fear_greed_score, 3),
            "on_chain": round(on_chain_score, 3)
        },
        "weights": weights
    }


def get_sentiment_analysis() -> Dict:
    """
    Get complete sentiment analysis from all available sources.
    
    Returns:
        Dict with sentiment scores, direction, and source details
    """
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "news": {},
        "social": {},
        "fear_greed": {},
        "on_chain": {},
        "aggregate": {},
        "error": None
    }
    
    try:
        # Fetch from all sources
        result["news"] = get_news_sentiment()
        result["social"] = get_social_sentiment()
        result["fear_greed"] = get_fear_greed_index()
        result["on_chain"] = get_on_chain_sentiment()
        
        # Calculate aggregate
        result["aggregate"] = calculate_aggregate_sentiment(
            result["news"],
            result["social"],
            result["fear_greed"],
            result["on_chain"]
        )
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def format_sentiment_message(sentiment: Dict) -> str:
    """Format sentiment analysis for Telegram notification."""
    agg = sentiment.get("aggregate", {})
    score = agg.get("aggregate_score", 0.0)
    direction = agg.get("direction", "NEUTRAL")
    
    emoji_map = {
        "BULLISH": "🟢",
        "BEARISH": "🔴",
        "NEUTRAL": "⚪"
    }
    
    emoji = emoji_map.get(direction, "❓")
    
    components = agg.get("components", {})
    fg = sentiment.get("fear_greed", {})
    
    msg = f"""{emoji} **Sentiment: {direction}** | Score: {score:+.3f}

📰 **News Sentiment:** {components.get('news', 0.0):+.3f}
   {sentiment.get('news', {}).get('articles_analyzed', 0)} articles analyzed

📱 **Social Sentiment:** {components.get('social', 0.0):+.3f}
   (Requires API access)

📊 **Fear & Greed Index:** {fg.get('value', 50)} ({fg.get('classification', 'Neutral')})
   Sentiment: {components.get('fear_greed', 0.0):+.3f}

⛓️ **On-Chain Sentiment:** {components.get('on_chain', 0.0):+.3f}
   (Requires blockchain data)

⏰ {sentiment.get('timestamp', '')[:19].replace('T', ' ')} UTC"""
    
    if sentiment.get("error"):
        msg += f"\n⚠️ Error: {sentiment['error']}"
    
    return msg


# Test
if __name__ == "__main__":
    print("Running sentiment analysis...")
    sentiment = get_sentiment_analysis()
    
    print("\n" + "="*50)
    print(format_sentiment_message(sentiment))
    print("="*50)
    
    print(f"\nRaw sentiment data: {json.dumps(sentiment, indent=2)}")
