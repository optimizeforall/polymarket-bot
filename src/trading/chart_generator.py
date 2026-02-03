"""
chart_generator.py - Generate visual charts for AI analysis

Creates candlestick charts with technical indicators for Opus to analyze visually.
Opus 4.5 has vision capabilities and can identify:
- Chart patterns (head & shoulders, triangles, channels)
- Support/resistance levels
- Candlestick patterns (doji, hammer, engulfing)
- Trend lines and momentum shifts

Charts generated:
1. 15-min candles (2 hours) - Immediate trading context
2. 1-hour candles (24 hours) - Daily trend
3. 4-hour candles (3 days) - Macro trend
"""

import io
import base64
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import numpy as np

# Chart styling - dark theme for clarity
CHART_STYLE = {
    'bg_color': '#1a1a2e',
    'grid_color': '#2d2d44',
    'text_color': '#e0e0e0',
    'up_color': '#00d26a',      # Green for up candles
    'down_color': '#ff4757',    # Red for down candles
    'volume_up': '#00d26a55',   # Transparent green
    'volume_down': '#ff475755', # Transparent red
    'vwap_color': '#ffd700',    # Gold for VWAP
    'ma_color': '#00bfff',      # Blue for moving average
    'rsi_color': '#ff69b4',     # Pink for RSI
}


def fetch_ohlcv_data(timeframe: str = "15m", limit: int = 100) -> List[Dict]:
    """
    Fetch OHLCV (Open, High, Low, Close, Volume) data from CryptoCompare.
    
    Args:
        timeframe: "15m", "1h", or "4h"
        limit: Number of candles to fetch
    
    Returns:
        List of candle dicts with timestamp, open, high, low, close, volume
    """
    # Map timeframe to API endpoint
    endpoint_map = {
        "15m": ("histominute", 15),  # 15-minute aggregation
        "1h": ("histohour", 1),
        "4h": ("histohour", 4),
    }
    
    endpoint, aggregate = endpoint_map.get(timeframe, ("histominute", 15))
    
    try:
        # CryptoCompare API
        if endpoint == "histominute":
            url = "https://min-api.cryptocompare.com/data/v2/histominute"
            params = {
                "fsym": "BTC",
                "tsym": "USD",
                "limit": limit * aggregate,  # Get more data for aggregation
                "aggregate": aggregate
            }
        else:
            url = "https://min-api.cryptocompare.com/data/v2/histohour"
            params = {
                "fsym": "BTC",
                "tsym": "USD",
                "limit": limit * aggregate if aggregate > 1 else limit,
                "aggregate": aggregate
            }
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if data.get("Response") == "Success" and data.get("Data", {}).get("Data"):
            candles = []
            raw_data = data["Data"]["Data"]
            
            # For 4h, aggregate hourly data
            if timeframe == "4h" and aggregate > 1:
                aggregated = []
                for i in range(0, len(raw_data), aggregate):
                    chunk = raw_data[i:i+aggregate]
                    if len(chunk) == aggregate:
                        aggregated.append({
                            "time": chunk[0]["time"],
                            "open": chunk[0]["open"],
                            "high": max(c["high"] for c in chunk),
                            "low": min(c["low"] for c in chunk),
                            "close": chunk[-1]["close"],
                            "volumefrom": sum(c.get("volumefrom", 0) for c in chunk)
                        })
                raw_data = aggregated
            
            for candle in raw_data[-limit:]:
                candles.append({
                    "timestamp": datetime.fromtimestamp(candle["time"], tz=timezone.utc),
                    "open": candle["open"],
                    "high": candle["high"],
                    "low": candle["low"],
                    "close": candle["close"],
                    "volume": candle.get("volumefrom", 0)
                })
            
            return candles
    except Exception as e:
        print(f"Error fetching {timeframe} data: {e}")
    
    return []


def calculate_vwap(candles: List[Dict]) -> List[float]:
    """Calculate VWAP for the candle series."""
    vwap_values = []
    cumulative_tp_vol = 0
    cumulative_vol = 0
    
    for candle in candles:
        typical_price = (candle["high"] + candle["low"] + candle["close"]) / 3
        volume = candle["volume"]
        
        cumulative_tp_vol += typical_price * volume
        cumulative_vol += volume
        
        if cumulative_vol > 0:
            vwap_values.append(cumulative_tp_vol / cumulative_vol)
        else:
            vwap_values.append(typical_price)
    
    return vwap_values


def calculate_rsi(candles: List[Dict], period: int = 14) -> List[Optional[float]]:
    """Calculate RSI for the candle series."""
    rsi_values = [None] * period
    
    if len(candles) < period + 1:
        return [None] * len(candles)
    
    # Calculate price changes
    changes = []
    for i in range(1, len(candles)):
        changes.append(candles[i]["close"] - candles[i-1]["close"])
    
    # Calculate initial average gain/loss
    gains = [max(0, c) for c in changes[:period]]
    losses = [abs(min(0, c)) for c in changes[:period]]
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    # First RSI
    if avg_loss == 0:
        rsi_values.append(100)
    else:
        rs = avg_gain / avg_loss
        rsi_values.append(100 - (100 / (1 + rs)))
    
    # Subsequent RSI values using smoothed method
    for i in range(period, len(changes)):
        gain = max(0, changes[i])
        loss = abs(min(0, changes[i]))
        
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        
        if avg_loss == 0:
            rsi_values.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - (100 / (1 + rs)))
    
    return rsi_values


def calculate_sma(candles: List[Dict], period: int = 20) -> List[Optional[float]]:
    """Calculate Simple Moving Average."""
    sma_values = [None] * (period - 1)
    
    for i in range(period - 1, len(candles)):
        window = candles[i - period + 1:i + 1]
        avg = sum(c["close"] for c in window) / period
        sma_values.append(avg)
    
    return sma_values


def draw_candlestick_chart(
    candles: List[Dict],
    title: str,
    timeframe: str,
    show_vwap: bool = True,
    show_sma: bool = True,
    show_rsi: bool = True,
    show_volume: bool = True,
    figsize: Tuple[int, int] = (12, 8)
) -> plt.Figure:
    """
    Draw a professional candlestick chart with indicators.
    
    Args:
        candles: List of OHLCV candles
        title: Chart title
        timeframe: For display purposes
        show_vwap: Show VWAP line
        show_sma: Show 20-period SMA
        show_rsi: Show RSI subplot
        show_volume: Show volume bars
        figsize: Figure size
    
    Returns:
        matplotlib Figure object
    """
    if not candles:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, "No data available", ha='center', va='center', fontsize=20)
        return fig
    
    style = CHART_STYLE
    
    # Create figure with subplots
    if show_rsi:
        fig, (ax_price, ax_rsi) = plt.subplots(
            2, 1, figsize=figsize,
            gridspec_kw={'height_ratios': [3, 1]},
            sharex=True
        )
    else:
        fig, ax_price = plt.subplots(figsize=figsize)
        ax_rsi = None
    
    fig.patch.set_facecolor(style['bg_color'])
    ax_price.set_facecolor(style['bg_color'])
    if ax_rsi:
        ax_rsi.set_facecolor(style['bg_color'])
    
    # Extract data
    timestamps = [c["timestamp"] for c in candles]
    opens = [c["open"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]
    volumes = [c["volume"] for c in candles]
    
    # Calculate candle width based on timeframe
    if len(timestamps) > 1:
        width = (timestamps[1] - timestamps[0]).total_seconds() / 86400 * 0.8  # 80% of interval
    else:
        width = 0.01
    
    # Draw candlesticks
    for i, candle in enumerate(candles):
        color = style['up_color'] if candle["close"] >= candle["open"] else style['down_color']
        
        # Candle body
        body_bottom = min(candle["open"], candle["close"])
        body_height = abs(candle["close"] - candle["open"])
        
        rect = Rectangle(
            (mdates.date2num(candle["timestamp"]) - width/2, body_bottom),
            width, body_height,
            facecolor=color,
            edgecolor=color,
            linewidth=0.5
        )
        ax_price.add_patch(rect)
        
        # Wicks
        ax_price.plot(
            [candle["timestamp"], candle["timestamp"]],
            [candle["low"], candle["high"]],
            color=color,
            linewidth=1
        )
    
    # Draw VWAP
    if show_vwap:
        vwap = calculate_vwap(candles)
        ax_price.plot(timestamps, vwap, color=style['vwap_color'], 
                     linewidth=1.5, label='VWAP', linestyle='--')
    
    # Draw SMA
    if show_sma:
        sma = calculate_sma(candles, 20)
        valid_sma = [(t, v) for t, v in zip(timestamps, sma) if v is not None]
        if valid_sma:
            sma_times, sma_vals = zip(*valid_sma)
            ax_price.plot(sma_times, sma_vals, color=style['ma_color'],
                         linewidth=1.5, label='SMA(20)')
    
    # Draw volume bars on secondary axis
    if show_volume:
        ax_vol = ax_price.twinx()
        ax_vol.set_facecolor('none')
        
        for i, candle in enumerate(candles):
            color = style['volume_up'] if candle["close"] >= candle["open"] else style['volume_down']
            ax_vol.bar(candle["timestamp"], candle["volume"], width=width,
                      color=color, alpha=0.5)
        
        ax_vol.set_ylim(0, max(volumes) * 4)  # Volume takes 25% of chart
        ax_vol.set_ylabel('Volume', color=style['text_color'], fontsize=10)
        ax_vol.tick_params(axis='y', colors=style['text_color'])
        ax_vol.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'))
    
    # Draw RSI
    if show_rsi and ax_rsi:
        rsi = calculate_rsi(candles)
        valid_rsi = [(t, v) for t, v in zip(timestamps, rsi) if v is not None]
        if valid_rsi:
            rsi_times, rsi_vals = zip(*valid_rsi)
            ax_rsi.plot(rsi_times, rsi_vals, color=style['rsi_color'], linewidth=1.5)
            ax_rsi.axhline(70, color='#ff4757', linestyle='--', alpha=0.5, linewidth=1)
            ax_rsi.axhline(30, color='#00d26a', linestyle='--', alpha=0.5, linewidth=1)
            ax_rsi.axhline(50, color=style['grid_color'], linestyle='-', alpha=0.3, linewidth=1)
            ax_rsi.fill_between(rsi_times, 70, 100, alpha=0.1, color='#ff4757')
            ax_rsi.fill_between(rsi_times, 0, 30, alpha=0.1, color='#00d26a')
        
        ax_rsi.set_ylim(0, 100)
        ax_rsi.set_ylabel('RSI', color=style['text_color'], fontsize=10)
        ax_rsi.tick_params(axis='both', colors=style['text_color'])
        ax_rsi.grid(True, color=style['grid_color'], alpha=0.3)
    
    # Styling
    ax_price.set_title(title, color=style['text_color'], fontsize=14, fontweight='bold', pad=10)
    ax_price.set_ylabel('Price (USD)', color=style['text_color'], fontsize=10)
    ax_price.tick_params(axis='both', colors=style['text_color'])
    ax_price.grid(True, color=style['grid_color'], alpha=0.3)
    ax_price.legend(loc='upper left', facecolor=style['bg_color'], 
                   edgecolor=style['grid_color'], labelcolor=style['text_color'])
    
    # Format x-axis
    if ax_rsi:
        ax_rsi.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M' if timeframe == "15m" else '%m/%d %H:%M'))
        plt.setp(ax_rsi.xaxis.get_majorticklabels(), rotation=45, ha='right')
    else:
        ax_price.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M' if timeframe == "15m" else '%m/%d %H:%M'))
        plt.setp(ax_price.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Add current price annotation
    current_price = closes[-1]
    ax_price.axhline(current_price, color=style['text_color'], linestyle=':', alpha=0.5)
    ax_price.annotate(
        f'${current_price:,.0f}',
        xy=(timestamps[-1], current_price),
        xytext=(10, 0),
        textcoords='offset points',
        color=style['text_color'],
        fontsize=10,
        fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.3', facecolor=style['bg_color'], edgecolor=style['text_color'])
    )
    
    # Price change annotation
    price_change = ((closes[-1] - opens[0]) / opens[0]) * 100
    change_color = style['up_color'] if price_change >= 0 else style['down_color']
    ax_price.text(
        0.02, 0.98, f'{price_change:+.2f}%',
        transform=ax_price.transAxes,
        color=change_color,
        fontsize=12,
        fontweight='bold',
        va='top'
    )
    
    plt.tight_layout()
    return fig


def generate_trading_charts(output_dir: str = "data/charts") -> Dict[str, str]:
    """
    Generate all trading charts and save to files.
    
    Returns:
        Dict mapping timeframe to file path
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    charts = {}
    
    # Chart configurations
    configs = [
        ("15m", 32, "BTC/USD - 15 Minute Candles (Last 8 Hours)"),
        ("1h", 24, "BTC/USD - 1 Hour Candles (Last 24 Hours)"),
        ("4h", 18, "BTC/USD - 4 Hour Candles (Last 3 Days)"),
    ]
    
    for timeframe, limit, title in configs:
        print(f"Generating {timeframe} chart...")
        candles = fetch_ohlcv_data(timeframe, limit)
        
        if candles:
            fig = draw_candlestick_chart(candles, title, timeframe)
            
            # Save to file
            filepath = f"{output_dir}/btc_{timeframe}.png"
            fig.savefig(filepath, dpi=150, bbox_inches='tight',
                       facecolor=CHART_STYLE['bg_color'])
            plt.close(fig)
            
            charts[timeframe] = filepath
            print(f"  ✓ Saved to {filepath}")
        else:
            print(f"  ✗ No data for {timeframe}")
    
    return charts


def chart_to_base64(filepath: str) -> Optional[str]:
    """Convert chart image to base64 for API transmission."""
    try:
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"Error encoding chart: {e}")
        return None


def get_charts_for_ai() -> Dict:
    """
    Generate charts and prepare for AI analysis.
    
    Returns:
        Dict with chart paths and base64 encoded images
    """
    charts = generate_trading_charts()
    
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "charts": {}
    }
    
    for timeframe, filepath in charts.items():
        result["charts"][timeframe] = {
            "path": filepath,
            "base64": chart_to_base64(filepath)
        }
    
    return result


# Test
if __name__ == "__main__":
    print("=" * 60)
    print("📊 BTC CHART GENERATOR")
    print("=" * 60)
    
    charts = generate_trading_charts()
    
    print("\n✅ Charts generated:")
    for tf, path in charts.items():
        print(f"   {tf}: {path}")
    
    print("\nOpen the PNG files to view the charts!")
