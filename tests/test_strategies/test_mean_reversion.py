from src.strategies.mean_reversion import compute
from src.strategies.base import SignalResult
import pandas as pd


def test_returns_signal_result(ranging_candles):
    assert isinstance(compute(ranging_candles), SignalResult)


def test_price_far_below_mean_gives_buy():
    # 30 bars at 1920, then sudden dip to 1900 (z-score << -1.5)
    stable = [1920.0] * 30
    dip = [1900.0] * 5
    closes = stable + dip
    df = pd.DataFrame({"close": closes})
    result = compute(df)
    assert result.signal == "BUY"


def test_price_far_above_mean_gives_sell():
    # 30 bars at 1900, then sudden spike to 1920 (z-score >> 1.5)
    stable = [1900.0] * 30
    spike = [1920.0] * 5
    closes = stable + spike
    df = pd.DataFrame({"close": closes})
    result = compute(df)
    assert result.signal == "SELL"


def test_short_candles_returns_neutral():
    df = pd.DataFrame({"close": [1900.0] * 5})
    assert compute(df).signal == "NEUTRAL"
