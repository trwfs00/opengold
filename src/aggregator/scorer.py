from dataclasses import dataclass, field
from src.strategies.base import SignalResult


@dataclass
class AggregateResult:
    buy_score: float
    sell_score: float
    regime: str
    signals: dict = field(default_factory=dict)


# Strategy weights per regime — NEUTRAL contributes zero regardless of weight
WEIGHTS: dict[str, dict[str, float]] = {
    "ma_crossover":       {"TRENDING_UP": 1.5, "TRENDING_DOWN": 1.5, "TRANSITIONAL": 1.0, "RANGING": 0.5, "BREAKOUT": 0.5},
    "macd":               {"TRENDING_UP": 1.5, "TRENDING_DOWN": 1.5, "TRANSITIONAL": 1.0, "RANGING": 0.5, "BREAKOUT": 0.8},
    "ichimoku":           {"TRENDING_UP": 1.5, "TRENDING_DOWN": 1.5, "TRANSITIONAL": 0.8, "RANGING": 0.3, "BREAKOUT": 0.5},
    "momentum":           {"TRENDING_UP": 1.2, "TRENDING_DOWN": 1.2, "TRANSITIONAL": 0.8, "RANGING": 0.3, "BREAKOUT": 1.0},
    "adx_trend":          {"TRENDING_UP": 1.5, "TRENDING_DOWN": 1.5, "TRANSITIONAL": 1.0, "RANGING": 0.3, "BREAKOUT": 0.8},
    "rsi":                {"TRENDING_UP": 0.3, "TRENDING_DOWN": 0.3, "TRANSITIONAL": 0.8, "RANGING": 1.5, "BREAKOUT": 0.5},
    "bollinger":          {"TRENDING_UP": 0.5, "TRENDING_DOWN": 0.5, "TRANSITIONAL": 1.0, "RANGING": 1.5, "BREAKOUT": 1.2},
    "stochastic":         {"TRENDING_UP": 0.3, "TRENDING_DOWN": 0.3, "TRANSITIONAL": 0.8, "RANGING": 1.5, "BREAKOUT": 0.5},
    "mean_reversion":     {"TRENDING_UP": 0.3, "TRENDING_DOWN": 0.3, "TRANSITIONAL": 0.5, "RANGING": 1.5, "BREAKOUT": 0.3},
    "breakout":           {"TRENDING_UP": 0.5, "TRENDING_DOWN": 0.5, "TRANSITIONAL": 0.8, "RANGING": 0.5, "BREAKOUT": 2.0},
    "support_resistance": {"TRENDING_UP": 0.8, "TRENDING_DOWN": 0.8, "TRANSITIONAL": 1.0, "RANGING": 1.0, "BREAKOUT": 1.5},
    "scalping":           {"TRENDING_UP": 0.8, "TRENDING_DOWN": 0.8, "TRANSITIONAL": 1.0, "RANGING": 1.0, "BREAKOUT": 1.0},
    "vwap":               {"TRENDING_UP": 1.0, "TRENDING_DOWN": 1.0, "TRANSITIONAL": 1.0, "RANGING": 1.0, "BREAKOUT": 1.0},
}


def aggregate(signals: list[SignalResult], regime: str) -> AggregateResult:
    buy_score = 0.0
    sell_score = 0.0
    signals_dict: dict = {}
    for s in signals:
        weight = WEIGHTS.get(s.name, {}).get(regime, 1.0)
        signals_dict[s.name] = {"signal": s.signal, "confidence": s.confidence}
        if s.signal == "BUY":
            buy_score += weight * s.confidence
        elif s.signal == "SELL":
            sell_score += weight * s.confidence
        # NEUTRAL → contributes zero
    return AggregateResult(
        buy_score=round(buy_score, 4),
        sell_score=round(sell_score, 4),
        regime=regime,
        signals=signals_dict,
    )
