import pandas as pd
import pandas_ta as ta
from src import config


def classify(candles: pd.DataFrame) -> str:
    """
    Returns market regime: BREAKOUT > TRENDING > RANGING (priority order).
    """
    min_len = max(config.ATR_LOOKBACK + 1, 20)
    if len(candles) < min_len:
        return "RANGING"

    # ── ATR spike → BREAKOUT ──────────────────────────────────────────────
    atr = ta.atr(candles["high"], candles["low"], candles["close"], length=config.ATR_LOOKBACK)
    if atr is not None and not atr.empty:
        atr_current = atr.iloc[-1]
        lookback_window = atr.iloc[-config.ATR_LOOKBACK:]
        # Use mean of prior bars (exclude the current spike itself for a fair comparison)
        atr_mean = atr.iloc[-(config.ATR_LOOKBACK + 1):-1].mean()
        if (
            not pd.isna(atr_current)
            and not pd.isna(atr_mean)
            and atr_mean > 0
            and atr_current > config.ATR_BREAKOUT_MULTIPLIER * atr_mean
        ):
            return "BREAKOUT"

    # ── ADX strong trend → TRENDING ───────────────────────────────────────
    adx_df = ta.adx(candles["high"], candles["low"], candles["close"], length=14)
    if adx_df is not None and not adx_df.empty:
        adx_val = adx_df["ADX_14"].iloc[-1]
        if not pd.isna(adx_val) and adx_val > config.ADX_TREND_THRESHOLD:
            return "TRENDING"

    return "RANGING"
