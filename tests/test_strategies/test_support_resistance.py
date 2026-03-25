from src.strategies.support_resistance import compute
from src.strategies.base import SignalResult
import pandas as pd


def test_returns_signal_result(ranging_candles):
    assert isinstance(compute(ranging_candles), SignalResult)


def test_price_near_support_gives_buy():
    # Build a range with a known support at 1900
    rows = []
    for i in range(20):
        rows.append({"high": 1920.0, "low": 1900.0, "close": 1910.0, "volume": 100.0})
    # Current bar: price touching support
    rows.append({"high": 1902.0, "low": 1899.5, "close": 1900.5, "volume": 200.0})
    df = pd.DataFrame(rows)
    result = compute(df)
    assert result.signal == "BUY"


def test_price_near_resistance_gives_sell():
    rows = []
    for i in range(20):
        rows.append({"high": 1920.0, "low": 1900.0, "close": 1910.0, "volume": 100.0})
    # Current bar: price touching resistance
    rows.append({"high": 1920.5, "low": 1918.0, "close": 1919.5, "volume": 200.0})
    df = pd.DataFrame(rows)
    result = compute(df)
    assert result.signal == "SELL"


def test_short_candles_returns_neutral():
    df = pd.DataFrame({
        "high": [1901.0] * 3,
        "low": [1899.0] * 3,
        "close": [1900.0] * 3,
        "volume": [100.0] * 3,
    })
    assert compute(df).signal == "NEUTRAL"
