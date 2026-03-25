from src.strategies.stochastic import compute
from src.strategies.base import SignalResult
import pandas as pd


def test_returns_signal_result(ranging_candles):
    assert isinstance(compute(ranging_candles), SignalResult)


def test_oversold_gives_buy():
    # Price hugging the lows → %K < 20
    n = 30
    highs = [1910.0] * n
    lows = [1900.0] * n
    closes = [1900.5] * n  # near lows
    df = pd.DataFrame({"high": highs, "low": lows, "close": closes})
    result = compute(df)
    assert result.signal == "BUY"


def test_overbought_gives_sell():
    # Price hugging the highs → %K > 80
    n = 30
    highs = [1910.0] * n
    lows = [1900.0] * n
    closes = [1909.5] * n  # near highs
    df = pd.DataFrame({"high": highs, "low": lows, "close": closes})
    result = compute(df)
    assert result.signal == "SELL"


def test_short_candles_returns_neutral():
    df = pd.DataFrame({"high": [1901.0] * 5, "low": [1899.0] * 5, "close": [1900.0] * 5})
    assert compute(df).signal == "NEUTRAL"
