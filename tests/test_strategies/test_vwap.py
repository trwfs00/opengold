from src.strategies.vwap import compute
from src.strategies.base import SignalResult
import pandas as pd


def test_returns_signal_result(ranging_candles):
    assert isinstance(compute(ranging_candles), SignalResult)


def test_price_below_vwap_gives_buy():
    # Volume-weighted price is 1915, current bar closes at 1900 → below VWAP
    rows = []
    for i in range(20):
        rows.append({"high": 1916.0, "low": 1914.0, "close": 1915.0, "volume": 1000.0})
    # Low-price bar with small volume → VWAP stays near 1915, close at 1900
    rows.append({"high": 1901.0, "low": 1899.0, "close": 1900.0, "volume": 1.0})
    df = pd.DataFrame(rows)
    result = compute(df)
    assert result.signal == "BUY"


def test_price_above_vwap_gives_sell():
    rows = []
    for i in range(20):
        rows.append({"high": 1901.0, "low": 1899.0, "close": 1900.0, "volume": 1000.0})
    rows.append({"high": 1921.0, "low": 1919.0, "close": 1920.0, "volume": 1.0})
    df = pd.DataFrame(rows)
    result = compute(df)
    assert result.signal == "SELL"


def test_short_candles_returns_neutral():
    df = pd.DataFrame({"high": [1901.0], "low": [1899.0], "close": [1900.0], "volume": [100.0]})
    assert compute(df).signal == "NEUTRAL"
