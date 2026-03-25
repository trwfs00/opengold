import pandas as pd
from src.strategies.base import SignalResult

NAME = "support_resistance"
PIVOT_PERIOD = 5
PROXIMITY_PCT = 0.002  # within 0.2% of level


def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < PIVOT_PERIOD * 2 + 1:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    prev = candles.iloc[-(PIVOT_PERIOD * 2):-PIVOT_PERIOD]
    price = candles["close"].iloc[-1]
    support = prev["low"].min()
    resistance = prev["high"].max()
    near_support = abs(price - support) / price < PROXIMITY_PCT
    near_resistance = abs(price - resistance) / price < PROXIMITY_PCT
    vol_col = "volume" if "volume" in candles.columns else None
    if vol_col:
        vol_avg = candles[vol_col].iloc[-20:].mean()
        vol_now = candles[vol_col].iloc[-1]
        vol_conf = min(1.0, vol_now / vol_avg) if vol_avg > 0 else 0.5
    else:
        vol_conf = 0.5
    if near_support:
        return SignalResult(name=NAME, signal="BUY", confidence=vol_conf * 0.7)
    if near_resistance:
        return SignalResult(name=NAME, signal="SELL", confidence=vol_conf * 0.7)
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
