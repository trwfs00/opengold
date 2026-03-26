from datetime import datetime, timezone
from src.aggregator.scorer import AggregateResult
from src import config


def _in_active_session() -> bool:
    """Return True if current UTC hour is within a configured trading session."""
    raw = config.TRADE_SESSIONS_UTC.strip()
    if raw == "0-24":
        return True
    hour = datetime.now(timezone.utc).hour
    for segment in raw.split(","):
        segment = segment.strip()
        if "-" not in segment:
            continue
        try:
            start, end = map(int, segment.split("-", 1))
            if start <= hour < end:
                return True
        except ValueError:
            continue
    return False


def should_trigger(agg: AggregateResult, open_trades: int, kill_switch: bool) -> bool:
    """Return True if the trade execution layer should be invoked."""
    if kill_switch:
        return False
    if open_trades >= config.MAX_CONCURRENT_TRADES:
        return False
    if not _in_active_session():
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
