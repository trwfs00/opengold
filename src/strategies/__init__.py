import logging
import pandas as pd
from src.strategies.base import SignalResult
from src.strategies import (
    ma_crossover, macd, ichimoku, momentum, adx_trend,
    rsi, bollinger, stochastic, mean_reversion,
    breakout, support_resistance, scalping, vwap,
)

_logger = logging.getLogger(__name__)

_ALL_STRATEGIES = [
    ma_crossover, macd, ichimoku, momentum, adx_trend,
    rsi, bollinger, stochastic, mean_reversion,
    breakout, support_resistance, scalping, vwap,
]


def run_all(candles: pd.DataFrame, regime: str) -> list[SignalResult]:
    """Run all 13 strategy modules and return their SignalResult list."""
    results = []
    for strategy in _ALL_STRATEGIES:
        try:
            results.append(strategy.compute(candles))
        except Exception as e:
            _logger.error(f"Strategy {strategy.__name__} failed: {e}", exc_info=True)
    return results
