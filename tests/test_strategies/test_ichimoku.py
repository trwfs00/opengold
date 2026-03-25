from src.strategies.ichimoku import compute
from src.strategies.base import SignalResult
import pandas as pd


def test_returns_signal_result(trending_up_candles):
    result = compute(trending_up_candles)
    assert isinstance(result, SignalResult)
    assert result.signal in ("BUY", "SELL", "NEUTRAL")


def test_uptrend_not_sell(trending_up_candles):
    result = compute(trending_up_candles)
    # In a strong uptrend, ichimoku should not signal SELL
    assert result.signal != "SELL"


def test_short_candles_returns_neutral():
    df = pd.DataFrame({
        "high": [1901.0] * 10,
        "low": [1899.0] * 10,
        "close": [1900.0] * 10,
    })
    assert compute(df).signal == "NEUTRAL"
