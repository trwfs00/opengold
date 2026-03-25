from src.strategies.breakout import compute
from src.strategies.base import SignalResult
import pandas as pd


def test_returns_signal_result(trending_up_candles):
    assert isinstance(compute(trending_up_candles), SignalResult)


def test_upside_breakout_gives_buy():
    # 25 stable bars at 1920, then a strong breakout above
    stable = [{"high": 1921.0, "low": 1919.0, "close": 1920.0}] * 25
    breakout_bar = {"high": 1935.0, "low": 1920.0, "close": 1934.0}
    rows = stable + [breakout_bar]
    df = pd.DataFrame(rows)
    result = compute(df)
    assert result.signal == "BUY"


def test_downside_breakout_gives_sell():
    stable = [{"high": 1921.0, "low": 1919.0, "close": 1920.0}] * 25
    breakout_bar = {"high": 1920.0, "low": 1906.0, "close": 1907.0}
    rows = stable + [breakout_bar]
    df = pd.DataFrame(rows)
    result = compute(df)
    assert result.signal == "SELL"


def test_short_candles_returns_neutral():
    df = pd.DataFrame({
        "high": [1901.0] * 5,
        "low": [1899.0] * 5,
        "close": [1900.0] * 5,
    })
    assert compute(df).signal == "NEUTRAL"
