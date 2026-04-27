"""
Helper utilities for CryptoPredict Agents.
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


def timestamp_now() -> str:
    """Get current ISO timestamp."""
    return datetime.utcnow().isoformat() + "Z"


def timeframe_to_minutes(timeframe: str) -> int:
    """Convert timeframe string to minutes."""
    mapping = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "4h": 240,
        "1d": 1440
    }
    return mapping.get(timeframe, 5)


def calculate_returns(prices: pd.Series) -> pd.Series:
    """Calculate log returns."""
    return np.log(prices / prices.shift(1)).dropna()


def calculate_volatility(returns: pd.Series, window: int = 20) -> float:
    """Calculate annualized volatility."""
    if len(returns) < window:
        return returns.std() * np.sqrt(252 * 24 * 12)  # Annualized for 5min data
    return returns.iloc[-window:].std() * np.sqrt(252 * 24 * 12)


def calculate_sharpe(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Calculate Sharpe ratio."""
    if returns.std() == 0:
        return 0.0
    return (returns.mean() - risk_free_rate) / returns.std()


def safe_json_loads(data: Any) -> Any:
    """Safely load JSON data."""
    if isinstance(data, dict):
        return data
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {"raw": data}
    return data


def hash_prediction(asset: str, timeframe: str, timestamp: str) -> str:
    """Generate a unique hash for a prediction."""
    content = f"{asset}:{timeframe}:{timestamp}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def format_price(price: float, decimals: int = 2) -> str:
    """Format price with appropriate decimals."""
    if price >= 1000:
        return f"${price:,.{decimals}f}"
    elif price >= 1:
        return f"${price:.{decimals}f}"
    else:
        return f"${price:.6f}"


def calculate_correlation_matrix(returns_dict: Dict[str, pd.Series]) -> pd.DataFrame:
    """Calculate correlation matrix between asset returns."""
    df = pd.DataFrame(returns_dict)
    return df.corr()


def detect_regime(prices: pd.Series, window: int = 20) -> str:
    """Detect market regime (trending/mean-reverting)."""
    if len(prices) < window * 2:
        return "unknown"
    
    returns = calculate_returns(prices)
    
    # Hurst exponent approximation
    lags = range(2, min(20, len(returns) // 4))
    tau = [np.std(np.subtract(returns[lag:], returns[:-lag])) for lag in lags]
    
    if len(tau) < 2:
        return "unknown"
    
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    hurst = poly[0]
    
    if hurst > 0.55:
        return "trending"
    elif hurst < 0.45:
        return "mean_reverting"
    else:
        return "random_walk"


def resample_ohlcv(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resample OHLCV data to a different timeframe."""
    freq_map = {
        "1m": "1min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "1h": "1H",
        "4h": "4H",
        "1d": "1D"
    }
    freq = freq_map.get(timeframe, "5min")
    
    resampled = df.resample(freq).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    }).dropna()
    
    return resampled


class CircularBuffer:
    """Thread-safe circular buffer for storing predictions."""
    
    def __init__(self, size: int = 1000):
        self.size = size
        self._buffer: List[Dict[str, Any]] = []
    
    def append(self, item: Dict[str, Any]):
        """Add item to buffer."""
        self._buffer.append(item)
        if len(self._buffer) > self.size:
            self._buffer.pop(0)
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all items."""
        return self._buffer.copy()
    
    def get_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get n most recent items."""
        return self._buffer[-n:]
    
    def filter_by(self, key: str, value: Any) -> List[Dict[str, Any]]:
        """Filter items by key-value pair."""
        return [item for item in self._buffer if item.get(key) == value]
    
    def clear(self):
        """Clear buffer."""
        self._buffer.clear()
