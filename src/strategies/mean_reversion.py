import pandas as pd
from src.strategies.base import SignalResult

NAME = "mean_reversion"
PERIOD = 20
THRESHOLD = 1.5


def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < PERIOD + 1:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    close = candles["close"]
    mean = close.rolling(PERIOD).mean().iloc[-1]
    std = close.rolling(PERIOD).std().iloc[-1]
    if pd.isna(std) or std == 0:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    z = (close.iloc[-1] - mean) / std
    if z < -THRESHOLD:
        return SignalResult(name=NAME, signal="BUY", confidence=min(1.0, abs(z) / 3.0))
    if z > THRESHOLD:
        return SignalResult(name=NAME, signal="SELL", confidence=min(1.0, z / 3.0))
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
