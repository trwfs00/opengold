from src.strategies.scalping import compute
from src.strategies.base import SignalResult
import pandas as pd


def test_returns_signal_result(trending_up_candles):
    assert isinstance(compute(trending_up_candles), SignalResult)


def test_uptrend_gives_buy(trending_up_candles):
    result = compute(trending_up_candles)
    assert result.signal == "BUY"


def test_downtrend_gives_sell(trending_down_candles):
    result = compute(trending_down_candles)
    assert result.signal == "SELL"


def test_short_candles_returns_neutral():
    df = pd.DataFrame({"close": [1900.0] * 5})
    assert compute(df).signal == "NEUTRAL"
