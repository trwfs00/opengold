import pandas as pd
import pandas_ta as ta
from src.strategies.base import SignalResult

NAME = "bollinger"


def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < 21:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    bb = ta.bbands(candles["close"], length=20, std=2)
    if bb is None or bb.empty:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    price = candles["close"].iloc[-1]
    lower_cols = [c for c in bb.columns if c.startswith("BBL_")]
    upper_cols = [c for c in bb.columns if c.startswith("BBU_")]
    if not lower_cols or not upper_cols:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    lower = bb[lower_cols[0]].iloc[-1]
    upper = bb[upper_cols[0]].iloc[-1]
    if pd.isna(lower) or pd.isna(upper):
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    band_width = upper - lower
    if band_width == 0:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    if price <= lower:
        conf = min(1.0, (lower - price) / band_width + 0.5)
        return SignalResult(name=NAME, signal="BUY", confidence=conf)
    if price >= upper:
        conf = min(1.0, (price - upper) / band_width + 0.5)
        return SignalResult(name=NAME, signal="SELL", confidence=conf)
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
