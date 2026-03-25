import pandas as pd
import numpy as np
import pytest


def _make_candles(n: int, trend: float, base_price: float = 1900.0, seed: int = 42) -> pd.DataFrame:
    """Build a synthetic OHLCV DataFrame with n rows."""
    rng = np.random.default_rng(seed)
    closes = base_price + trend * np.arange(n) + rng.normal(0, 0.5, n)
    highs = closes + rng.uniform(0.1, 1.0, n)
    lows = closes - rng.uniform(0.1, 1.0, n)
    opens = np.roll(closes, 1)
    opens[0] = base_price
    volumes = rng.integers(100, 1000, n).astype(float)
    times = pd.date_range("2024-01-01", periods=n, freq="1min")
    return pd.DataFrame(
        {"time": times, "open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes}
    )


@pytest.fixture
def trending_up_candles() -> pd.DataFrame:
    """200 candles with a clear upward trend (~0.5 pts/bar)."""
    return _make_candles(200, trend=0.5)


@pytest.fixture
def trending_down_candles() -> pd.DataFrame:
    """200 candles with a clear downward trend (~-0.5 pts/bar)."""
    return _make_candles(200, trend=-0.5)


@pytest.fixture
def ranging_candles() -> pd.DataFrame:
    """200 candles with no trend (flat mean-reversion regime)."""
    return _make_candles(200, trend=0.0)
