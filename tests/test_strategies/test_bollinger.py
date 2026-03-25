from src.strategies.bollinger import compute
from src.strategies.base import SignalResult
import pandas as pd


def test_returns_signal_result(ranging_candles):
    assert isinstance(compute(ranging_candles), SignalResult)


def test_price_at_lower_band_gives_buy():
    # 27 bars stable at 1920, then 3 bars at 1880 → price is extreme outlier below lower band
    stable = [1920.0] * 27
    dip = [1880.0] * 3
    closes = stable + dip
    df = pd.DataFrame({"close": closes})
    result = compute(df)
    assert result.signal == "BUY"


def test_price_at_upper_band_gives_sell():
    # 27 bars stable at 1900, then 3 bars at 1940 → price is extreme outlier above upper band
    stable = [1900.0] * 27
    spike = [1940.0] * 3
    closes = stable + spike
    df = pd.DataFrame({"close": closes})
    result = compute(df)
    assert result.signal == "SELL"


def test_short_candles_returns_neutral():
    df = pd.DataFrame({"close": [1900.0] * 5})
    assert compute(df).signal == "NEUTRAL"
