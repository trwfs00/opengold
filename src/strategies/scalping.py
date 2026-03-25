import pandas as pd
import pandas_ta as ta
from src.strategies.base import SignalResult

NAME = "scalping"


def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < 15:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    ema5 = ta.ema(candles["close"], length=5)
    ema13 = ta.ema(candles["close"], length=13)
    if ema5 is None or ema13 is None:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    curr5, curr13 = ema5.iloc[-1], ema13.iloc[-1]
    if pd.isna(curr5) or pd.isna(curr13):
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    gap = abs(curr5 - curr13) / curr13
    conf = min(1.0, gap * 1000)
    if curr5 > curr13:
        return SignalResult(name=NAME, signal="BUY", confidence=conf)
    if curr5 < curr13:
        return SignalResult(name=NAME, signal="SELL", confidence=conf)
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
