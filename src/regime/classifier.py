import pandas as pd
import pandas_ta as ta
from src import config


def classify(candles: pd.DataFrame) -> str:
    """
    Returns market regime:
      BREAKOUT > TRENDING_UP | TRENDING_DOWN > TRANSITIONAL > RANGING
    """
    min_len = max(config.ATR_LOOKBACK + 1, 20)
    if len(candles) < min_len:
        return "RANGING"

    # ── ATR spike → BREAKOUT ──────────────────────────────────────────────
    atr = ta.atr(candles["high"], candles["low"], candles["close"], length=config.ATR_LOOKBACK)
    if atr is not None and not atr.empty:
        atr_current = atr.iloc[-1]
        # Use mean of prior bars (exclude the current spike itself for a fair comparison)
        atr_mean = atr.iloc[-(config.ATR_LOOKBACK + 1):-1].mean()
        if (
            not pd.isna(atr_current)
            and not pd.isna(atr_mean)
            and atr_mean > 0
            and atr_current > config.ATR_BREAKOUT_MULTIPLIER * atr_mean
        ):
            return "BREAKOUT"

    # ── ADX / DI lines ────────────────────────────────────────────────────
    adx_df = ta.adx(candles["high"], candles["low"], candles["close"], length=14)
    if adx_df is not None and not adx_df.empty:
        adx_val = adx_df["ADX_14"].iloc[-1]
        if not pd.isna(adx_val):
            if adx_val > config.ADX_TREND_THRESHOLD:
                # Strong trend — determine direction via DI+ vs DI-
                dmp = adx_df.get("DMP_14")
                dmn = adx_df.get("DMN_14")
                if dmp is not None and dmn is not None:
                    dmp_val = dmp.iloc[-1]
                    dmn_val = dmn.iloc[-1]
                    if not pd.isna(dmp_val) and not pd.isna(dmn_val):
                        return "TRENDING_UP" if dmp_val >= dmn_val else "TRENDING_DOWN"
                return "TRENDING_UP"  # fallback if DI columns missing
            # Weak/building trend — transitional zone (ADX between threshold-8 and threshold)
            if adx_val > max(config.ADX_TREND_THRESHOLD - 8, 10):
                return "TRANSITIONAL"

    return "RANGING"
