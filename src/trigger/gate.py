from src.aggregator.scorer import AggregateResult
from src import config


def should_trigger(agg: AggregateResult, open_trades: int, kill_switch: bool) -> bool:
    """Return True if the trade execution layer should be invoked."""
    if kill_switch:
        return False
    if open_trades >= config.MAX_CONCURRENT_TRADES:
        return False
    max_score = max(agg.buy_score, agg.sell_score)
    if max_score < config.TRIGGER_MIN_SCORE:
        return False
    if abs(agg.buy_score - agg.sell_score) < config.TRIGGER_MIN_SCORE_DIFF:
        return False
    return True


def get_direction(agg: AggregateResult) -> str:
    """Return 'BUY' or 'SELL' based on dominant score."""
    return "BUY" if agg.buy_score >= agg.sell_score else "SELL"
