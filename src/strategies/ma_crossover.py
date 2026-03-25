import pandas as pd
from src.strategies.base import SignalResult

NAME = "ma_crossover"
FAST = 9
SLOW = 21


def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < SLOW + 1:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    close = candles["close"]
    fast_ma = close.rolling(FAST).mean()
    slow_ma = close.rolling(SLOW).mean()
    curr_fast, curr_slow = fast_ma.iloc[-1], slow_ma.iloc[-1]
    prev_fast, prev_slow = fast_ma.iloc[-2], slow_ma.iloc[-2]
    if pd.isna(curr_fast) or pd.isna(curr_slow):
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    gap = abs(curr_fast - curr_slow) / curr_slow
    # Fresh crossover → higher confidence
    if prev_fast <= prev_slow and curr_fast > curr_slow:
        return SignalResult(name=NAME, signal="BUY", confidence=min(1.0, gap * 500))
    if prev_fast >= prev_slow and curr_fast < curr_slow:
        return SignalResult(name=NAME, signal="SELL", confidence=min(1.0, gap * 500))
    # Trend continuation
    if curr_fast > curr_slow:
        return SignalResult(name=NAME, signal="BUY", confidence=min(1.0, gap * 500))
    if curr_fast < curr_slow:
        return SignalResult(name=NAME, signal="SELL", confidence=min(1.0, gap * 500))
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
