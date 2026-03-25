from src.strategies.rsi import compute
from src.strategies.base import SignalResult
import numpy as np
import pandas as pd


def test_returns_signal_result(ranging_candles):
    assert isinstance(compute(ranging_candles), SignalResult)


def test_oversold_gives_buy():
    # Prices diving sharply → RSI < 30
    n = 50
    closes = [1950.0 - i * 3 for i in range(n)]  # strong down-move
    df = pd.DataFrame({"close": closes})
    result = compute(df)
    assert result.signal == "BUY"


def test_overbought_gives_sell():
    # Prices rising sharply → RSI > 70
    n = 50
    closes = [1900.0 + i * 3 for i in range(n)]
    df = pd.DataFrame({"close": closes})
    result = compute(df)
    assert result.signal == "SELL"


def test_short_candles_returns_neutral():
    df = pd.DataFrame({"close": [1900.0] * 5})
    assert compute(df).signal == "NEUTRAL"
