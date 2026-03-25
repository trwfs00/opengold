import pandas as pd
import pandas_ta as ta
from src.strategies.base import SignalResult
from src import config

NAME = "adx_trend"


def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < 20:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    adx_df = ta.adx(candles["high"], candles["low"], candles["close"], length=14)
    if adx_df is None or adx_df.empty:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    adx = adx_df["ADX_14"].iloc[-1]
    dmp = adx_df["DMP_14"].iloc[-1]
    dmn = adx_df["DMN_14"].iloc[-1]
    if pd.isna(adx) or pd.isna(dmp) or pd.isna(dmn):
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    if adx < config.ADX_TREND_THRESHOLD:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    confidence = min(1.0, (adx - config.ADX_TREND_THRESHOLD) / 25.0)
    if dmp > dmn:
        return SignalResult(name=NAME, signal="BUY", confidence=confidence)
    return SignalResult(name=NAME, signal="SELL", confidence=confidence)
