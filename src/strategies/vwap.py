import pandas as pd
from src.strategies.base import SignalResult

NAME = "vwap"


def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < 2:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    df = candles.copy()
    df["typical"] = (df["high"] + df["low"] + df["close"]) / 3
    df["cum_vol"] = df["volume"].cumsum()
    df["cum_tp_vol"] = (df["typical"] * df["volume"]).cumsum()
    cum_vol_last = df["cum_vol"].iloc[-1]
    if cum_vol_last == 0:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    vwap = df["cum_tp_vol"].iloc[-1] / cum_vol_last
    price = df["close"].iloc[-1]
    if pd.isna(vwap) or vwap == 0:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    deviation = (price - vwap) / vwap
    if deviation < -0.001:
        return SignalResult(name=NAME, signal="BUY", confidence=min(1.0, abs(deviation) * 200))
    if deviation > 0.001:
        return SignalResult(name=NAME, signal="SELL", confidence=min(1.0, deviation * 200))
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
