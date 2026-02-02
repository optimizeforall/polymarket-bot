"""
indicators.py - Technical indicators for BTC trading signals

Implements:
- RSI (Relative Strength Index) - 14 period default
- VWAP (Volume Weighted Average Price) - 15-minute window
- Momentum - 60-second price change
- Moving averages for trend confirmation
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, List


def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """
    Calculate RSI (Relative Strength Index).
    
    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss over period
    
    Args:
        prices: List of prices (oldest to newest)
        period: RSI period (default 14)
    
    Returns:
        RSI value (0-100) or None if insufficient data
    """
    if len(prices) < period + 1:
        return None
    
    # Calculate price changes
    changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    
    # Separate gains and losses
    gains = [max(0, c) for c in changes]
    losses = [abs(min(0, c)) for c in changes]
    
    # Use only the last 'period' changes for calculation
    recent_gains = gains[-(period):]
    recent_losses = losses[-(period):]
    
    avg_gain = sum(recent_gains) / period
    avg_loss = sum(recent_losses) / period
    
    if avg_loss == 0:
        return 100.0  # No losses = max RSI
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return round(rsi, 2)


def calculate_vwap(prices: List[float], volumes: List[float]) -> Optional[float]:
    """
    Calculate VWAP (Volume Weighted Average Price).
    
    VWAP = Σ(Price × Volume) / Σ(Volume)
    
    Args:
        prices: List of prices
        volumes: List of corresponding volumes
    
    Returns:
        VWAP value or None if insufficient data
    """
    if not prices or not volumes or len(prices) != len(volumes):
        return None
    
    total_volume = sum(volumes)
    if total_volume == 0:
        # Fallback to simple average if no volume data
        return sum(prices) / len(prices)
    
    price_volume_sum = sum(p * v for p, v in zip(prices, volumes))
    vwap = price_volume_sum / total_volume
    
    return round(vwap, 2)


def calculate_momentum(prices: List[float], lookback_seconds: int = 60, 
                       interval_seconds: int = 5) -> Optional[float]:
    """
    Calculate price momentum over a time window.
    
    Momentum = (Current Price - Price N seconds ago) / Price N seconds ago * 100
    
    Args:
        prices: List of prices (oldest to newest)
        lookback_seconds: How far back to look (default 60s)
        interval_seconds: Time between price samples (default 5s)
    
    Returns:
        Momentum as percentage change, or None if insufficient data
    """
    samples_needed = lookback_seconds // interval_seconds
    
    if len(prices) < samples_needed + 1:
        return None
    
    current_price = prices[-1]
    past_price = prices[-(samples_needed + 1)]
    
    if past_price == 0:
        return None
    
    momentum = ((current_price - past_price) / past_price) * 100
    return round(momentum, 4)


def calculate_sma(prices: List[float], period: int) -> Optional[float]:
    """
    Calculate Simple Moving Average.
    
    Args:
        prices: List of prices
        period: Number of periods to average
    
    Returns:
        SMA value or None if insufficient data
    """
    if len(prices) < period:
        return None
    
    return round(sum(prices[-period:]) / period, 2)


def calculate_ema(prices: List[float], period: int) -> Optional[float]:
    """
    Calculate Exponential Moving Average.
    
    EMA = Price × k + EMA_prev × (1 - k)
    where k = 2 / (period + 1)
    
    Args:
        prices: List of prices
        period: EMA period
    
    Returns:
        EMA value or None if insufficient data
    """
    if len(prices) < period:
        return None
    
    k = 2 / (period + 1)
    
    # Start with SMA for first EMA value
    ema = sum(prices[:period]) / period
    
    # Calculate EMA for remaining prices
    for price in prices[period:]:
        ema = price * k + ema * (1 - k)
    
    return round(ema, 2)


def calculate_vwap_deviation(current_price: float, vwap: float) -> float:
    """
    Calculate percentage deviation from VWAP.
    
    Args:
        current_price: Current BTC price
        vwap: VWAP value
    
    Returns:
        Percentage deviation (positive = above VWAP, negative = below)
    """
    if vwap == 0:
        return 0.0
    
    deviation = ((current_price - vwap) / vwap) * 100
    return round(deviation, 4)


def calculate_trend(prices: List[float], short_period: int = 5, 
                    long_period: int = 20) -> str:
    """
    Determine trend direction using moving average crossover.
    
    Args:
        prices: List of prices
        short_period: Short MA period
        long_period: Long MA period
    
    Returns:
        'UP', 'DOWN', or 'NEUTRAL'
    """
    short_ma = calculate_sma(prices, short_period)
    long_ma = calculate_sma(prices, long_period)
    
    if short_ma is None or long_ma is None:
        return 'NEUTRAL'
    
    diff_pct = ((short_ma - long_ma) / long_ma) * 100
    
    if diff_pct > 0.05:
        return 'UP'
    elif diff_pct < -0.05:
        return 'DOWN'
    else:
        return 'NEUTRAL'


class IndicatorCalculator:
    """
    Wrapper class to calculate all indicators from price data.
    Designed to work with the CSV format from logger.py
    """
    
    def __init__(self, csv_path: str = "btc_prices.csv"):
        self.csv_path = csv_path
        self.df = None
        self.last_load = None
    
    def load_data(self, minutes: int = 15) -> bool:
        """Load recent price data from CSV."""
        try:
            self.df = pd.read_csv(self.csv_path)
            self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
            
            # Filter to recent data only (timezone-aware)
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            self.df = self.df[self.df['timestamp'] > cutoff]
            
            self.last_load = datetime.utcnow()
            return len(self.df) > 0
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def get_all_indicators(self) -> Dict:
        """
        Calculate all indicators from loaded data.
        
        Returns dict with:
        - current_price
        - rsi_14
        - vwap_15m
        - vwap_deviation_pct
        - momentum_60s
        - trend
        - data_points
        """
        if self.df is None or len(self.df) == 0:
            return {"error": "No data loaded"}
        
        prices = self.df['price'].tolist()
        volumes = self.df['volume_24h'].tolist()
        
        current_price = prices[-1] if prices else None
        
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "current_price": current_price,
            "rsi_14": calculate_rsi(prices, 14),
            "vwap_15m": calculate_vwap(prices, volumes),
            "vwap_deviation_pct": calculate_vwap_deviation(
                current_price, 
                calculate_vwap(prices, volumes)
            ) if current_price else None,
            "momentum_60s": calculate_momentum(prices, 60, 5),
            "trend": calculate_trend(prices),
            "sma_20": calculate_sma(prices, 20),
            "ema_12": calculate_ema(prices, 12),
            "data_points": len(prices)
        }


def get_current_indicators(csv_path: str = "btc_prices.csv") -> Dict:
    """
    Convenience function to get current indicators.
    
    Usage:
        from indicators import get_current_indicators
        signals = get_current_indicators()
        print(signals['rsi_14'], signals['vwap_deviation_pct'])
    """
    calc = IndicatorCalculator(csv_path)
    if calc.load_data(minutes=15):
        return calc.get_all_indicators()
    return {"error": "Failed to load price data"}


# Test
if __name__ == "__main__":
    print("Testing indicators with live data...")
    indicators = get_current_indicators()
    
    print("\n📊 Current Indicators:")
    for key, value in indicators.items():
        print(f"  {key}: {value}")
