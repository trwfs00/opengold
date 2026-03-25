from src.strategies.adx_trend import compute
from src.strategies.base import SignalResult
import pandas as pd


def test_returns_signal_result(trending_up_candles):
    assert isinstance(compute(trending_up_candles), SignalResult)


def test_uptrend_gives_buy(trending_up_candles):
    result = compute(trending_up_candles)
    # Strong trend → ADX > 25; DI+ > DI- in uptrend
    assert result.signal == "BUY"


def test_short_candles_returns_neutral():
    df = pd.DataFrame({
        "high": [1901.0] * 5,
        "low": [1899.0] * 5,
        "close": [1900.0] * 5,
    })
    assert compute(df).signal == "NEUTRAL"
