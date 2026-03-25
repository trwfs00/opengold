import pandas as pd
import pandas_ta as ta
from src.strategies.base import SignalResult

NAME = "momentum"
PERIOD = 10
THRESHOLD = 0.2  # 0.2% ROC required


def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < PERIOD + 1:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    roc = ta.roc(candles["close"], length=PERIOD)
    if roc is None or roc.empty or pd.isna(roc.iloc[-1]):
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    value = roc.iloc[-1]
    if value > THRESHOLD:
        return SignalResult(name=NAME, signal="BUY", confidence=min(1.0, value / 2.0))
    if value < -THRESHOLD:
        return SignalResult(name=NAME, signal="SELL", confidence=min(1.0, abs(value) / 2.0))
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
