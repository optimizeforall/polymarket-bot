"""
ai_consensus_signal.py - AI Trading System with Full Context

Architecture:
1. Sonnet 3.5 (CHEAP ~$0.004) - Pre-filter: "Is this worth analyzing?"
   - If NO → HOLD, save money
   - If YES → Call Opus

2. Opus 4.5 (BEST ~$0.02-0.05) - Final decision maker with FULL CONTEXT
   - Multi-timeframe BTC analysis (4h, 24h, 3d trends)
   - Order book depth and imbalance (research: #1 predictor)
   - Sentiment analysis (news, Fear/Greed index)
   - Polymarket market prices and implied probability
   - Recent trade history for self-reflection
   - Chain-of-thought reasoning

The goal: Give Opus the fullest possible picture to make genuinely
informed decisions, not just react to indicators.
"""

import os
import json
import requests
from datetime import datetime, timezone
from typing import Dict, Optional, List
from decouple import config

# Import context builder (try both relative and absolute)
try:
    from .context_builder import build_full_context, format_context_for_prompt
    CONTEXT_BUILDER_AVAILABLE = True
except ImportError:
    try:
        from context_builder import build_full_context, format_context_for_prompt
        CONTEXT_BUILDER_AVAILABLE = True
    except ImportError:
        CONTEXT_BUILDER_AVAILABLE = False

# Import chart generator
try:
    from .chart_generator import generate_trading_charts, chart_to_base64
    CHART_GENERATOR_AVAILABLE = True
except ImportError:
    try:
        from chart_generator import generate_trading_charts, chart_to_base64
        CHART_GENERATOR_AVAILABLE = True
    except ImportError:
        CHART_GENERATOR_AVAILABLE = False

OPENROUTER_API_KEY = config("OPENROUTER_API_KEY", default=None)

# Models via OpenRouter
MODELS = {
    "sonnet": "anthropic/claude-3.5-sonnet",  # Cheap pre-filter
    "opus": "anthropic/claude-opus-4.5",  # Final decision maker
}


def build_prefilter_prompt(indicators: Dict, market_info: Dict) -> str:
    """Sonnet pre-filter: Is this worth deeper analysis?"""
    return f"""You are a trading signal PRE-FILTER. Quickly decide if conditions warrant calling our expensive AI (Opus 4.5).

## Current Data
- BTC Price: ${indicators.get('current_price', 0):,.2f}
- RSI (14): {indicators.get('rsi_14', 'N/A')}
- VWAP Deviation: {indicators.get('vwap_deviation_pct', 'N/A')}%
- 60s Momentum: {indicators.get('momentum_60s', 'N/A')}%
- Time Remaining: {market_info.get('time_until_end_min', 'N/A')} minutes
- Market UP Price: {market_info.get('up_price', 'N/A')}
- Market DOWN Price: {market_info.get('down_price', 'N/A')}

## REJECT (save money) if ANY:
- RSI between 45-55 (no direction)
- Momentum between -0.02% and +0.02% (flat)
- Time < 4 min or > 13 min (bad timing)

## APPROVE (call Opus) if:
- Clear signals (RSI < 40 or > 60)
- Strong momentum (|momentum| > 0.03%)
- Good timing (4-12 min remaining)

Respond with ONLY:
```json
{{
  "worth_analyzing": true | false,
  "likely_direction": "UP" | "DOWN" | "UNCLEAR",
  "reason": "One sentence"
}}
```"""


def build_opus_prompt(indicators: Dict, market_info: Dict, prefilter_hint: str, full_context: Optional[Dict] = None) -> str:
    """
    Opus 4.5 final decision prompt with FULL CONTEXT and chain-of-thought reasoning.
    
    Based on prompt engineering research:
    - Chain-of-thought prompting improves complex reasoning
    - Least-to-most decomposition helps with multi-factor analysis
    - Self-consistency through structured reasoning
    """
    
    # Build context section - this is the comprehensive view
    if full_context and CONTEXT_BUILDER_AVAILABLE:
        context_str = format_context_for_prompt(full_context)
    else:
        # Fallback to basic context
        context_str = f"""
BASIC CONTEXT (full context unavailable):
- BTC Price: ${indicators.get('current_price', 0):,.2f}
- RSI (14): {indicators.get('rsi_14', 'N/A')}
- VWAP Deviation: {indicators.get('vwap_deviation_pct', 'N/A')}%
- 60s Momentum: {indicators.get('momentum_60s', 'N/A')}%
- Trend: {indicators.get('trend', 'N/A')}
"""
    
    return f"""You are Claude Opus 4.5, the FINAL DECISION MAKER for a BTC trading bot on Polymarket.

You're trading 15-minute BTC prediction markets. Your job is to analyze ALL available data
and make the best possible decision. This is a $100 account - every dollar matters.

{context_str}

## Pre-filter Assessment
Sonnet 3.5 thinks: {prefilter_hint}

---

## YOUR ANALYSIS PROCESS

Think through this step by step. Consider each factor before deciding.

### STEP 1: Visual Chart Analysis (if charts provided)
Look at the attached charts and identify:
- Overall trend direction from the candlestick patterns
- Support/resistance levels where price has bounced or rejected
- Chart patterns: triangles, channels, head & shoulders, double tops/bottoms
- Candlestick patterns: doji, hammer, engulfing, etc.
- Volume confirmation: is volume supporting the price move?
- RSI divergences: is RSI confirming or diverging from price?

### STEP 2: Multi-Timeframe Trend Analysis
Consider the larger picture from the data:
- What is the 4-hour trend telling us?
- What is the 24-hour trend telling us?
- What is the 3-day trend telling us?
- Is the short-term move aligned with the larger trend, or counter-trend?

### STEP 2: Technical Indicator Assessment
Now analyze the 15-minute signals:
- RSI: <30 oversold (potential bounce), >70 overbought (potential drop), 45-55 neutral
- VWAP: Price above = bullish bias, below = bearish bias
- Momentum: The immediate direction of price movement

### STEP 3: Order Book Analysis (CRITICAL - Research shows this is #1 predictor)
If order book data is available:
- Bid/Ask imbalance: Positive = more buying pressure, Negative = more selling
- Liquidity score: Higher = safer to trade, Lower = beware of slippage
- Spread: Wide spread = illiquid market, avoid

### STEP 4: Sentiment Check
What's the market mood?
- Fear & Greed Index: Extreme fear can mean bounce opportunity, extreme greed = caution
- News sentiment: Any major headlines affecting direction?

### STEP 5: Value Assessment (This is key for edge)
Check the Polymarket prices:
- If you think UP: Is the UP token < 55%? (Good value) or > 60%? (Already priced in)
- If you think DOWN: Is the DOWN token < 55%? (Good value) or > 60%? (Already priced in)
- The market is ALREADY making a prediction - you need EDGE to profit

### STEP 6: Risk/Reward Evaluation
Given the $100 account with 7% max position ($7):
- Is the potential reward worth the risk?
- Am I being greedy or is this genuinely a good setup?
- When in doubt, HOLD. Missing a trade costs nothing.

---

## FINAL DECISION

After considering all factors above, make your call.

Respond with ONLY this JSON:
```json
{{
  "signal": "BUY" | "SELL" | "HOLD",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "reasoning": "Your complete analysis (3-4 sentences covering key factors)",
  "key_factors": ["factor1", "factor2", "factor3"],
  "concerns": ["any risks or uncertainties"],
  "edge_explanation": "Why this trade has positive expected value, or why HOLD"
}}
```

## Trading Rules
- BUY = Bet BTC ends higher than current price (buy UP token)
- SELL = Bet BTC ends lower than current price (buy DOWN token)  
- HOLD = No trade (this is ALWAYS acceptable)

## Position Sizing (automatic based on confidence)
- HIGH confidence = 7% of account ($7)
- MEDIUM confidence = 3.5% of account ($3.50)
- LOW confidence = DO NOT TRADE

## Capital Preservation Principles
1. A HOLD is always acceptable. Missing a trade costs $0.
2. A bad trade costs real money. Be selective.
3. Only trade when multiple factors align.
4. If the market has already priced in your prediction (>55-60%), the value is gone.
5. Counter-trend trades require HIGHER conviction than trend-following trades.

Make your decision. Be thorough. Be honest about uncertainty.
"""


def call_openrouter(prompt: str, model_key: str, timeout: int = 60, images: Optional[List[str]] = None) -> Optional[Dict]:
    """
    Call OpenRouter API, optionally with images for vision analysis.
    
    Args:
        prompt: Text prompt
        model_key: "sonnet" or "opus"
        timeout: Request timeout
        images: Optional list of base64-encoded images
    """
    if not OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY not set")
        return None
    
    model_id = MODELS.get(model_key)
    if not model_id:
        print(f"❌ Unknown model: {model_key}")
        return None
    
    try:
        # Opus needs more tokens for chain-of-thought analysis
        max_tokens = 1200 if model_key == "opus" else 400
        
        # Build message content (text only or text + images)
        if images:
            # Multi-modal message with images
            content = [{"type": "text", "text": prompt}]
            for img_base64 in images:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img_base64}"
                    }
                })
            messages = [{"role": "user", "content": content}]
        else:
            # Text-only message
            messages = [{"role": "user", "content": prompt}]
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://polymarket-bot.local",
            },
            json={
                "model": model_id,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.3  # Slightly higher for more nuanced reasoning
            },
            timeout=timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Parse JSON
            try:
                start = content.find("{")
                end = content.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(content[start:end])
            except json.JSONDecodeError:
                print(f"JSON parse error from {model_key}")
                print(f"Content: {content[:200]}")
        else:
            print(f"API error {response.status_code} from {model_key}: {response.text[:100]}")
        
        return None
        
    except requests.exceptions.Timeout:
        print(f"Timeout calling {model_key}")
        return None
    except Exception as e:
        print(f"Error calling {model_key}: {e}")
        return None


def get_consensus_signal(indicators: Dict, market_info: Dict, sentiment: Optional[Dict] = None, include_charts: bool = True) -> Dict:
    """
    Get trading signal: Sonnet pre-filter → Opus final decision with FULL CONTEXT + CHARTS.
    
    This function:
    1. Runs Sonnet as a cheap pre-filter
    2. If worthwhile, builds comprehensive context (multi-timeframe, order book, sentiment)
    3. Generates visual charts for pattern recognition
    4. Sends everything to Opus for chain-of-thought analysis with vision
    
    Args:
        indicators: Current technical indicators
        market_info: Polymarket market information
        sentiment: Optional sentiment analysis
        include_charts: Whether to generate and send charts to Opus (adds ~$0.02-0.03)
    """
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signal": "HOLD",
        "confidence": "LOW",
        "position_size_pct": 0.0,
        "prefilter_passed": False,
        "prefilter_response": None,
        "opus_response": None,
        "reasoning": "",
        "key_factors": [],
        "concerns": [],
        "edge_explanation": "",
        "cost_saved": False,
        "full_context_used": False,
        "charts_used": False,
        "error": None
    }
    
    # Step 1: Sonnet pre-filter (cheap check first)
    print("🔍 Sonnet 3.5 pre-filtering...")
    prefilter_prompt = build_prefilter_prompt(indicators, market_info)
    prefilter = call_openrouter(prefilter_prompt, "sonnet", timeout=30)
    
    if not prefilter:
        result["error"] = "Pre-filter failed"
        result["reasoning"] = "Sonnet unavailable - defaulting to HOLD"
        return result
    
    result["prefilter_response"] = prefilter
    worth_it = prefilter.get("worth_analyzing", False)
    direction_hint = prefilter.get("likely_direction", "UNCLEAR")
    
    print(f"   Worth analyzing: {worth_it}")
    print(f"   Direction hint: {direction_hint}")
    print(f"   Reason: {prefilter.get('reason', 'N/A')}")
    
    if not worth_it:
        result["cost_saved"] = True
        result["reasoning"] = f"Pre-filter rejected: {prefilter.get('reason', 'No clear signal')}"
        return result
    
    result["prefilter_passed"] = True
    
    # Step 2: Build FULL CONTEXT for Opus (this is where we invest in getting it right)
    full_context = None
    if CONTEXT_BUILDER_AVAILABLE:
        print("📊 Building comprehensive context...")
        try:
            full_context = build_full_context(indicators, market_info, sentiment)
            result["full_context_used"] = True
            
            # Log what context we gathered
            summary = full_context.get("summary", {})
            print(f"   • BTC 4h trend: {summary.get('trend_4h', 'N/A')}")
            print(f"   • BTC 24h trend: {summary.get('trend_24h', 'N/A')}")
            print(f"   • Fear/Greed: {summary.get('fear_greed', 'N/A')}")
            print(f"   • Market lean: {summary.get('market_lean', 'N/A')}")
        except Exception as e:
            print(f"   ⚠️ Context builder error: {e}")
    else:
        print("   ⚠️ Context builder not available - using basic context")
    
    # Step 3: Generate charts for visual analysis (optional, adds cost)
    chart_images = []
    if include_charts and CHART_GENERATOR_AVAILABLE:
        print("📈 Generating charts for visual analysis...")
        try:
            charts = generate_trading_charts()
            for timeframe in ["15m", "1h", "4h"]:
                if timeframe in charts:
                    img_b64 = chart_to_base64(charts[timeframe])
                    if img_b64:
                        chart_images.append(img_b64)
                        print(f"   ✓ {timeframe} chart ready")
            
            if chart_images:
                result["charts_used"] = True
                print(f"   📊 {len(chart_images)} charts will be analyzed")
        except Exception as e:
            print(f"   ⚠️ Chart generation error: {e}")
    
    # Step 4: Opus final decision with full context + charts
    print("🧠 Opus 4.5 analyzing with full context" + (" + charts..." if chart_images else "..."))
    opus_prompt = build_opus_prompt(
        indicators, 
        market_info, 
        f"{direction_hint} - {prefilter.get('reason', '')}",
        full_context
    )
    
    # Give Opus more time for thorough analysis (especially with images)
    timeout = 180 if chart_images else 120
    opus = call_openrouter(opus_prompt, "opus", timeout=timeout, images=chart_images if chart_images else None)
    
    if not opus:
        result["error"] = "Opus failed to respond"
        result["reasoning"] = "Opus unavailable - defaulting to HOLD"
        return result
    
    result["opus_response"] = opus
    
    # Extract Opus decision (now includes more fields)
    result["signal"] = opus.get("signal", "HOLD")
    result["confidence"] = opus.get("confidence", "LOW")
    result["reasoning"] = opus.get("reasoning", "No reasoning provided")
    result["key_factors"] = opus.get("key_factors", [])
    result["concerns"] = opus.get("concerns", [])
    result["edge_explanation"] = opus.get("edge_explanation", "")
    
    # Calculate position size based on confidence
    if result["confidence"] == "HIGH":
        result["position_size_pct"] = 0.07  # 7%
    elif result["confidence"] == "MEDIUM":
        result["position_size_pct"] = 0.035  # 3.5%
    else:
        result["position_size_pct"] = 0.0
    
    print(f"   Opus decision: {result['signal']} ({result['confidence']})")
    print(f"   Reasoning: {result['reasoning'][:150]}...")
    if result["key_factors"]:
        print(f"   Key factors: {', '.join(result['key_factors'][:3])}")
    if result["concerns"]:
        print(f"   Concerns: {', '.join(result['concerns'][:2])}")
    
    return result


def format_consensus_message(result: Dict, market_info: Dict = None, indicators: Dict = None, balance: float = 100.0) -> str:
    """Format for Telegram notification with comprehensive analysis."""
    prefilter = result.get("prefilter_response") or {}
    opus = result.get("opus_response") or {}
    
    # Extract market and price info
    market_title = market_info.get('title', 'BTC 15-min') if market_info else 'BTC 15-min'
    time_remaining = market_info.get('time_until_end_min', 'N/A') if market_info else 'N/A'
    btc_price = indicators.get('current_price', 0) if indicators else 0
    up_price = market_info.get('up_price', 0.5) if market_info else 0.5
    down_price = market_info.get('down_price', 0.5) if market_info else 0.5
    
    # Format time remaining
    time_str = f"{time_remaining:.1f} min" if isinstance(time_remaining, (int, float)) else str(time_remaining)
    
    # Header with context
    header = f"""⏰ *{market_title}*
💵 BTC: ${btc_price:,.0f} | ⏳ {time_str} left
📈 UP: {up_price*100:.0f}% | 📉 DOWN: {down_price*100:.0f}%
💰 Balance: ${balance:.2f}
"""
    
    if result.get("cost_saved"):
        return header + f"""
⚪ *HOLD - Pre-filter Rejected*

🔍 *Sonnet 3.5*: Not worth analyzing
📝 {prefilter.get('reason', 'No clear signal')}

💰 Saved ~$0.03 by skipping Opus"""
    
    if result.get("signal") in ["BUY", "SELL"]:
        emoji = "🟢" if result["signal"] == "BUY" else "🔴"
        direction = "UP" if result["signal"] == "BUY" else "DOWN"
        position_dollars = result['position_size_pct'] * balance
        
        # Build key factors string
        factors = result.get('key_factors', [])
        factors_str = '• ' + '\n• '.join(factors) if factors else 'N/A'
        
        # Build concerns string
        concerns = result.get('concerns', [])
        concerns_str = '• ' + '\n• '.join(concerns) if concerns else 'None noted'
        
        msg = header + f"""
{emoji} *{result['signal']}* ({result['confidence']}) - Bet {direction}

📊 *Position*: {result['position_size_pct']*100:.1f}% (~${position_dollars:.2f})

🔍 *Sonnet Pre-filter*: ✅ {prefilter.get('likely_direction', 'N/A')}

🧠 *Opus 4.5 Analysis*:
{result.get('reasoning', 'N/A')}

🎯 *Key Factors*:
{factors_str}

⚠️ *Concerns*:
{concerns_str}

💡 *Edge*: {result.get('edge_explanation', 'N/A')[:150]}"""
        
        context_items = []
        if result.get("full_context_used"):
            context_items.append("multi-TF data")
        if result.get("charts_used"):
            context_items.append("visual charts")
        
        if context_items:
            msg += f"\n\n📈 Analysis used: {', '.join(context_items)}"
        
        return msg
    
    else:
        return header + f"""
⚪ *HOLD* - No Trade

🔍 *Sonnet*: {prefilter.get('likely_direction', 'N/A')}
🧠 *Opus*: {result.get('signal', 'HOLD')} ({result.get('confidence', 'LOW')})

📝 *Analysis*:
{result.get('reasoning', 'No clear opportunity')}

💡 *Why no trade*: {result.get('edge_explanation', 'Insufficient edge or high uncertainty')}"""


# Test
if __name__ == "__main__":
    print("="*60)
    print("🤖 AI SIGNAL TEST (Sonnet → Opus)")
    print("="*60)
    
    if not OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY not set")
        exit(1)
    
    # Test with bullish data
    test_indicators = {
        "current_price": 78650.00,
        "rsi_14": 63.5,
        "vwap_deviation_pct": 0.25,
        "momentum_60s": 0.09,
        "trend": "UP",
        "data_points": 180
    }
    
    test_market = {
        "title": "Bitcoin Up or Down - Test",
        "time_until_end_min": 9.0,
        "up_price": 0.47,
        "down_price": 0.53
    }
    
    print(f"\n📊 Test Data:")
    print(f"   Price: ${test_indicators['current_price']:,.2f}")
    print(f"   RSI: {test_indicators['rsi_14']} (bullish zone)")
    print(f"   VWAP: +{test_indicators['vwap_deviation_pct']}%")
    print(f"   Momentum: +{test_indicators['momentum_60s']}%")
    print(f"   Time left: {test_market['time_until_end_min']} min")
    
    print(f"\n🔄 Getting AI signal...")
    result = get_consensus_signal(test_indicators, test_market)
    
    print(f"\n" + "="*60)
    print(format_consensus_message(result))
    print("="*60)
