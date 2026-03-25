import pandas as pd
import pandas_ta as ta
from src.strategies.base import SignalResult

NAME = "macd"


def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < 35:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    macd_df = ta.macd(candles["close"], fast=12, slow=26, signal=9)
    if macd_df is None or macd_df.empty:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    # Use MACD line vs zero-line: positive = EMA12 > EMA26 = bullish trend
    macd_col = [c for c in macd_df.columns if c.startswith("MACD_") and not c.startswith("MACDh_") and not c.startswith("MACDs_")]
    if not macd_col:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    macd_val = macd_df[macd_col[0]].iloc[-1]
    if pd.isna(macd_val):
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    # Confidence scaled by magnitude; typical intraday MACD range ~1–5 for XAU/USD M1
    confidence = min(1.0, abs(macd_val) / 5.0)
    if macd_val > 0:
        return SignalResult(name=NAME, signal="BUY", confidence=confidence)
    if macd_val < 0:
        return SignalResult(name=NAME, signal="SELL", confidence=confidence)
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
