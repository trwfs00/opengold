import pandas as pd
import pandas_ta as ta
from src.strategies.base import SignalResult

NAME = "breakout"
PERIOD = 20


def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < PERIOD + 2:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    lookback = candles.iloc[-(PERIOD + 1):-1]
    current = candles.iloc[-1]
    high_20 = lookback["high"].max()
    low_20 = lookback["low"].min()
    atr = ta.atr(candles["high"], candles["low"], candles["close"], length=14)
    atr_val = atr.iloc[-1] if atr is not None and not pd.isna(atr.iloc[-1]) else 1.0
    if current["close"] > high_20:
        conf = min(1.0, (current["close"] - high_20) / atr_val)
        return SignalResult(name=NAME, signal="BUY", confidence=conf)
    if current["close"] < low_20:
        conf = min(1.0, (low_20 - current["close"]) / atr_val)
        return SignalResult(name=NAME, signal="SELL", confidence=conf)
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
