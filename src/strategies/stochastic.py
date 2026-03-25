import pandas as pd
import pandas_ta as ta
from src.strategies.base import SignalResult

NAME = "stochastic"


def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < 17:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    stoch = ta.stoch(candles["high"], candles["low"], candles["close"], k=14, d=3)
    if stoch is None or stoch.empty:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    k_cols = [c for c in stoch.columns if c.startswith("STOCHk_")]
    if not k_cols:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    k = stoch[k_cols[0]].iloc[-1]
    if pd.isna(k):
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    if k < 20:
        return SignalResult(name=NAME, signal="BUY", confidence=min(1.0, (20 - k) / 20))
    if k > 80:
        return SignalResult(name=NAME, signal="SELL", confidence=min(1.0, (k - 80) / 20))
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
