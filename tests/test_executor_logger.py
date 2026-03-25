from src.executor.orders import sync_positions
from src.logger.writer import (
    log_decision, log_trade,
    get_kill_switch_state, set_kill_switch,
    get_daily_start_balance, set_daily_start_balance,
)
from src.db import execute
from datetime import datetime, timezone


# ── executor unit tests (pure Python, no MT5) ─────────────────────────────────

def test_sync_positions_detects_closed():
    prev = [{"ticket": 1}, {"ticket": 2}]
    # Only ticket 2 remains open
    closed, current = sync_positions(prev, lambda: [{"ticket": 2}])
    assert len(closed) == 1
    assert closed[0]["ticket"] == 1


def test_sync_positions_no_closed():
    prev = [{"ticket": 1}]
    closed, current = sync_positions(prev, lambda: [{"ticket": 1}])
    assert closed == []


def test_sync_positions_all_closed():
    prev = [{"ticket": 1}, {"ticket": 2}]
    closed, current = sync_positions(prev, lambda: [])
    assert len(closed) == 2


# ── logger integration tests (require live TimescaleDB) ─────────────────────

def test_log_decision_writes_row():
    before = execute("SELECT COUNT(*) FROM decisions", fetch=True)[0][0]
    log_decision("TRENDING", 7.2, 1.1, True, "BUY", 0.8, 1910.0, 1940.0, None)
    after = execute("SELECT COUNT(*) FROM decisions", fetch=True)[0][0]
    assert after == before + 1


def test_log_trade_writes_row():
    now = datetime.now(timezone.utc)
    before = execute("SELECT COUNT(*) FROM trades", fetch=True)[0][0]
    log_trade(now, now, "BUY", 0.01, 1920.0, 1930.0, 1910.0, 1940.0, 100.0)
    after = execute("SELECT COUNT(*) FROM trades", fetch=True)[0][0]
    assert after == before + 1


def test_kill_switch_round_trip():
    set_kill_switch(True)
    assert get_kill_switch_state() is True
    set_kill_switch(False)
    assert get_kill_switch_state() is False


def test_daily_balance_round_trip():
    set_daily_start_balance(12345.67)
    balance, date_str = get_daily_start_balance()
    assert abs(balance - 12345.67) < 0.01
    from datetime import datetime, timezone
    assert date_str == datetime.now(timezone.utc).date().isoformat()
