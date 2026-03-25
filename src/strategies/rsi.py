import pandas as pd
import pandas_ta as ta
from src.strategies.base import SignalResult

NAME = "rsi"


def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < 15:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    rsi = ta.rsi(candles["close"], length=14)
    if rsi is None or pd.isna(rsi.iloc[-1]):
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    value = rsi.iloc[-1]
    if value < 30:
        return SignalResult(name=NAME, signal="BUY", confidence=min(1.0, (30 - value) / 30))
    if value > 70:
        return SignalResult(name=NAME, signal="SELL", confidence=min(1.0, (value - 70) / 30))
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
