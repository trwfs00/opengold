from src.trigger.gate import should_trigger, get_direction
from src.aggregator.scorer import AggregateResult
from src import config as _config


def _agg(buy=7.0, sell=1.0, regime="TRENDING"):
    return AggregateResult(buy_score=buy, sell_score=sell, regime=regime, signals={})


def test_strong_buy_triggers():
    assert should_trigger(_agg(7.0, 1.0), open_trades=0, kill_switch=False) is True


def test_kill_switch_blocks():
    assert should_trigger(_agg(7.0, 1.0), open_trades=0, kill_switch=True) is False


def test_low_score_no_trigger():
    assert should_trigger(_agg(3.0, 1.0), open_trades=0, kill_switch=False) is False


def test_score_conflict_no_trigger():
    # Buy and sell scores within 2.0 → ambiguous, no trigger
    assert should_trigger(_agg(5.5, 5.0), open_trades=0, kill_switch=False) is False


def test_max_trades_blocks(monkeypatch):
    monkeypatch.setattr(_config, "MAX_CONCURRENT_TRADES", 3)
    monkeypatch.setattr(_config, "TRADE_SESSIONS_UTC", "0-24")
    assert should_trigger(_agg(7.0, 1.0), open_trades=3, kill_switch=False) is False


def test_get_direction_buy():
    assert get_direction(_agg(7.0, 1.0)) == "BUY"


def test_get_direction_sell():
    assert get_direction(_agg(1.0, 8.0)) == "SELL"
