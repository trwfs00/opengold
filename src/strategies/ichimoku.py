import pandas as pd
from src.strategies.base import SignalResult

NAME = "ichimoku"


def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < 52:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    high = candles["high"]
    low = candles["low"]
    close = candles["close"]
    # Tenkan-sen: 9-period midpoint
    tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
    # Kijun-sen: 26-period midpoint
    kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
    # Senkou Span A = (tenkan + kijun) / 2, projected 26 bars forward
    # Cloud values affecting now were computed 26 bars ago
    span_a = (tenkan + kijun) / 2
    # Senkou Span B = 52-period midpoint, projected 26 bars forward
    span_b = (high.rolling(52).max() + low.rolling(52).min()) / 2
    # Index into values that form the current cloud (26 bars ago)
    if len(span_a) < 27:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    cloud_a = span_a.iloc[-27]
    cloud_b = span_b.iloc[-27]
    if pd.isna(cloud_a) or pd.isna(cloud_b):
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    price = close.iloc[-1]
    cloud_top = max(cloud_a, cloud_b)
    cloud_bot = min(cloud_a, cloud_b)
    if price > cloud_top:
        dist = (price - cloud_top) / price
        return SignalResult(name=NAME, signal="BUY", confidence=min(1.0, dist * 50))
    if price < cloud_bot:
        dist = (cloud_bot - price) / price
        return SignalResult(name=NAME, signal="SELL", confidence=min(1.0, dist * 50))
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
