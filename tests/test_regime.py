from src.regime.classifier import classify
import pandas as pd


def test_returns_valid_regime(trending_up_candles):
    result = classify(trending_up_candles)
    assert result in ("TRENDING", "RANGING", "BREAKOUT")


def test_trending_regime(trending_up_candles):
    result = classify(trending_up_candles)
    assert result == "TRENDING"


def test_ranging_regime(ranging_candles):
    result = classify(ranging_candles)
    assert result == "RANGING"


def test_short_candles_returns_ranging():
    df = pd.DataFrame({
        "high": [1901.0] * 5,
        "low": [1899.0] * 5,
        "close": [1900.0] * 5,
        "volume": [100.0] * 5,
    })
    assert classify(df) == "RANGING"


def test_breakout_regime():
    # 30 quiet candles then an explosive ATR spike
    quiet = [{"high": 1901.0, "low": 1899.0, "close": 1900.0} for _ in range(30)]
    # ATR spike: high-low = 50 pts vs avg ~2 pts → 25x multiplier, well above 1.5x threshold
    spike = [{"high": 1950.0, "low": 1900.0, "close": 1948.0}]
    df = pd.DataFrame(quiet + spike)
    result = classify(df)
    assert result == "BREAKOUT"
