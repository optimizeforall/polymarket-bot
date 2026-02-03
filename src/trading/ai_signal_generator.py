"""
ai_signal_generator.py - Use Claude/Opus 4.5 as the trading brain

This module calls Claude to analyze market conditions and make trading decisions.
It can use either:
1. Direct Anthropic API (requires ANTHROPIC_API_KEY)
2. OpenRouter (cheaper, requires OPENROUTER_API_KEY)

Cost considerations:
- Opus 4.5 via Anthropic: ~$15/M input, $75/M output tokens
- Opus 4.5 via OpenRouter: ~$15/M input, $75/M output tokens  
- Sonnet 3.5: ~$3/M input, $15/M output (good balance)
- Haiku 3: ~$0.25/M input, $1.25/M output (cheapest)

For trading, we recommend Sonnet 3.5 - smart enough, 5x cheaper than Opus.
"""

import os
import json
import requests
from datetime import datetime, timezone
from typing import Dict, Optional
from decouple import config

# Try to load API keys
ANTHROPIC_API_KEY = config("ANTHROPIC_API_KEY", default=None)
OPENROUTER_API_KEY = config("OPENROUTER_API_KEY", default=None)

# Model options (in order of preference for trading)
MODELS = {
    "opus": "claude-3-5-opus-20240620",      # Most capable, expensive
    "sonnet": "claude-3-5-sonnet-20241022",  # Good balance (recommended)
    "haiku": "claude-3-haiku-20240307",      # Fast and cheap
}

# Default to Sonnet for cost efficiency
DEFAULT_MODEL = "sonnet"


def get_trading_prompt(indicators: Dict, market_info: Dict, recent_signals: list = None) -> str:
    """
    Build the prompt for Claude to analyze and make a trading decision.
    """
    recent_signals_text = ""
    if recent_signals:
        recent_signals_text = f"""
Recent signals (last 5):
{json.dumps(recent_signals[-5:], indent=2)}
"""

    return f"""You are a BTC trading analyst for 15-minute prediction markets on Polymarket.

## Current Market Data
- **Price**: ${indicators.get('current_price', 0):,.2f}
- **RSI (14)**: {indicators.get('rsi_14', 'N/A')}
- **VWAP Deviation**: {indicators.get('vwap_deviation_pct', 'N/A')}%
- **60s Momentum**: {indicators.get('momentum_60s', 'N/A')}%
- **Trend**: {indicators.get('trend', 'N/A')}
- **Data Points**: {indicators.get('data_points', 0)}

## Market Info
- **Market**: {market_info.get('title', 'BTC 15-min Up/Down')}
- **Time Remaining**: {market_info.get('time_until_end_min', 'N/A')} minutes
- **Current UP Price**: {market_info.get('up_price', 'N/A')} ({float(market_info.get('up_price', 0.5))*100:.0f}% implied)
- **Current DOWN Price**: {market_info.get('down_price', 'N/A')} ({float(market_info.get('down_price', 0.5))*100:.0f}% implied)
{recent_signals_text}

## Your Task
Analyze the data and decide: Should we bet UP, DOWN, or HOLD?

Consider:
1. RSI levels (30-50 bearish, 50-70 bullish, extremes = caution)
2. VWAP deviation (positive = bullish, negative = bearish)
3. Momentum direction
4. Time remaining (need 5+ minutes for position to play out)
5. Market pricing (is there value vs our prediction?)

## Response Format
Respond with ONLY a JSON object:
```json
{{
  "signal": "BUY" | "SELL" | "HOLD",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "reasoning": "Brief explanation (1-2 sentences)",
  "position_size_pct": 0.0 to 0.10
}}
```

Rules:
- BUY = bet on UP outcome
- SELL = bet on DOWN outcome  
- HOLD = no trade
- HIGH confidence = 10% position, MEDIUM = 5%, LOW = 0%
- If uncertain, HOLD. Capital preservation > profit.
"""


def call_anthropic_api(prompt: str, model: str = DEFAULT_MODEL) -> Optional[Dict]:
    """Call Anthropic API directly."""
    if not ANTHROPIC_API_KEY:
        return None
    
    model_id = MODELS.get(model, MODELS[DEFAULT_MODEL])
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": model_id,
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("content", [{}])[0].get("text", "")
            
            # Parse JSON from response
            try:
                # Find JSON in response
                start = content.find("{")
                end = content.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(content[start:end])
            except json.JSONDecodeError:
                pass
        
        return None
        
    except Exception as e:
        print(f"Anthropic API error: {e}")
        return None


def call_openrouter_api(prompt: str, model: str = DEFAULT_MODEL) -> Optional[Dict]:
    """Call OpenRouter API (often cheaper)."""
    if not OPENROUTER_API_KEY:
        return None
    
    # OpenRouter model names
    openrouter_models = {
        "opus": "anthropic/claude-3.5-opus",
        "sonnet": "anthropic/claude-3.5-sonnet",
        "haiku": "anthropic/claude-3-haiku",
    }
    
    model_id = openrouter_models.get(model, openrouter_models[DEFAULT_MODEL])
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Parse JSON from response
            try:
                start = content.find("{")
                end = content.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(content[start:end])
            except json.JSONDecodeError:
                pass
        
        return None
        
    except Exception as e:
        print(f"OpenRouter API error: {e}")
        return None


def get_ai_signal(indicators: Dict, market_info: Dict, 
                  recent_signals: list = None,
                  model: str = DEFAULT_MODEL,
                  provider: str = "auto") -> Dict:
    """
    Get trading signal from Claude AI.
    
    Args:
        indicators: Dict from get_current_indicators()
        market_info: Dict from get_current_tradeable_market()
        recent_signals: List of recent signal dicts for context
        model: "opus", "sonnet", or "haiku"
        provider: "anthropic", "openrouter", or "auto"
    
    Returns:
        Signal dict with signal, confidence, reasoning, position_size_pct
    """
    # Build prompt
    prompt = get_trading_prompt(indicators, market_info, recent_signals)
    
    # Try to get AI response
    result = None
    
    if provider == "auto":
        # Try OpenRouter first (often cheaper), then Anthropic
        result = call_openrouter_api(prompt, model)
        if not result:
            result = call_anthropic_api(prompt, model)
    elif provider == "openrouter":
        result = call_openrouter_api(prompt, model)
    elif provider == "anthropic":
        result = call_anthropic_api(prompt, model)
    
    # If AI call failed, return HOLD
    if not result:
        return {
            "signal": "HOLD",
            "confidence": "LOW",
            "reasoning": "AI analysis unavailable - defaulting to HOLD",
            "position_size_pct": 0.0,
            "ai_used": False
        }
    
    # Add metadata
    result["ai_used"] = True
    result["model"] = model
    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    
    return result


def estimate_cost(model: str = DEFAULT_MODEL) -> str:
    """Estimate cost per signal."""
    # Approximate tokens per call: ~800 input, ~100 output
    costs = {
        "opus": "$0.015 per signal",
        "sonnet": "$0.004 per signal", 
        "haiku": "$0.0003 per signal"
    }
    return costs.get(model, "unknown")


# Test
if __name__ == "__main__":
    print("AI Signal Generator")
    print("="*50)
    
    # Check API keys
    print(f"Anthropic API: {'✅ Set' if ANTHROPIC_API_KEY else '❌ Not set'}")
    print(f"OpenRouter API: {'✅ Set' if OPENROUTER_API_KEY else '❌ Not set'}")
    
    if not ANTHROPIC_API_KEY and not OPENROUTER_API_KEY:
        print("\n⚠️ No API keys found!")
        print("Add one of these to your .env file:")
        print("  ANTHROPIC_API_KEY=sk-ant-...")
        print("  OPENROUTER_API_KEY=sk-or-...")
    else:
        print(f"\nEstimated costs:")
        for model in ["haiku", "sonnet", "opus"]:
            print(f"  {model}: {estimate_cost(model)}")
        
        print(f"\nRecommended: sonnet (best balance of cost/quality)")
