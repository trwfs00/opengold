import json
import logging
from datetime import datetime, timezone
from src.db import execute

logger = logging.getLogger(__name__)


def log_position_event(
    ticket: int,
    event_type: str,
    direction: str,
    price: float,
    old_sl: float | None = None,
    new_sl: float | None = None,
    reasoning: str | None = None,
):
    """Record a position manager action (TRAIL_BE, TRAIL_SL, REEVAL_HOLD, REEVAL_CLOSE)."""
    try:
        execute(
            """INSERT INTO position_events
               (ticket, event_type, direction, old_sl, new_sl, price, reasoning)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (
                int(ticket),
                str(event_type),
                str(direction),
                float(old_sl) if old_sl is not None else None,
                float(new_sl) if new_sl is not None else None,
                float(price),
                reasoning,
            ),
        )
    except Exception as e:
        logger.error(f"log_position_event failed: {e}")


def log_decision(
    regime: str,
    buy_score: float,
    sell_score: float,
    trigger_fired: bool,
    ai_action: str | None = None,
    ai_confidence: float | None = None,
    ai_sl: float | None = None,
    ai_tp: float | None = None,
    risk_block_reason: str | None = None,
    signals: dict | None = None,
    ai_reasoning: str | None = None,
):
    try:
        execute(
            """INSERT INTO decisions
               (time, regime, buy_score, sell_score, trigger_fired,
                ai_action, ai_confidence, ai_sl, ai_tp, risk_block_reason, signals, ai_reasoning)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                datetime.now(timezone.utc),
                str(regime),
                float(buy_score),
                float(sell_score),
                bool(trigger_fired),
                str(ai_action) if ai_action is not None else None,
                float(ai_confidence) if ai_confidence is not None else None,
                float(ai_sl) if ai_sl is not None else None,
                float(ai_tp) if ai_tp is not None else None,
                risk_block_reason,
                json.dumps(signals) if signals is not None else None,
                ai_reasoning,
            ),
        )
    except Exception as e:
        logger.error(f"log_decision failed: {e}")


def log_trade(
    open_time,
    close_time,
    direction: str,
    lot_size: float,
    open_price: float,
    close_price: float,
    sl: float,
    tp: float,
    pnl: float,
):
    result = "WIN" if pnl > 1.0 else "LOSS" if pnl < -1.0 else "BREAKEVEN"
    try:
        execute(
            """INSERT INTO trades
               (open_time, close_time, direction, lot_size,
                open_price, close_price, sl, tp, pnl, result)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (open_time, close_time, str(direction),
             float(lot_size), float(open_price), float(close_price),
             float(sl), float(tp), float(pnl), result),
        )
    except Exception as e:
        logger.error(f"log_trade failed: {e}")


def check_and_log_trade_no_duplicate(
    open_time,
    close_time,
    direction: str,
    lot_size: float,
    open_price: float,
    close_price: float,
    sl: float,
    tp: float,
    pnl: float,
):
    """Log trade only if no matching row exists (dedup by open_time+direction+open_price)."""
    existing = execute(
        "SELECT 1 FROM trades WHERE open_time=%s AND direction=%s AND open_price=%s",
        (open_time, direction, open_price),
        fetch=True,
    )
    if not existing:
        log_trade(open_time, close_time, direction, lot_size, open_price, close_price, sl, tp, pnl)


def get_kill_switch_state() -> bool:
    rows = execute(
        "SELECT key, value FROM system_state WHERE key IN ('kill_switch_active','kill_switch_date')",
        fetch=True,
    )
    state = {r[0]: r[1] for r in rows} if rows else {}
    active = state.get("kill_switch_active", "false") == "true"
    ks_date = state.get("kill_switch_date", "")
    today_utc = datetime.now(timezone.utc).date().isoformat()
    if active and ks_date != today_utc:
        # Auto-reset at UTC midnight
        set_kill_switch(False)
        return False
    return active


def set_kill_switch(active: bool):
    value = "true" if active else "false"
    today_utc = datetime.now(timezone.utc).date().isoformat()
    execute(
        "UPDATE system_state SET value=%s, updated_at=NOW() WHERE key='kill_switch_active'",
        (value,),
    )
    execute(
        "UPDATE system_state SET value=%s, updated_at=NOW() WHERE key='kill_switch_date'",
        (today_utc,),
    )


def get_daily_start_balance() -> tuple[float, str]:
    """Returns (balance, date_utc_iso) stored for the current day's baseline."""
    rows = execute(
        "SELECT key, value FROM system_state WHERE key IN ('daily_start_balance','daily_start_date')",
        fetch=True,
    )
    state = {r[0]: r[1] for r in rows} if rows else {}
    try:
        balance = float(state.get("daily_start_balance", "0"))
    except ValueError:
        balance = 0.0
    date_str = state.get("daily_start_date", "")
    return balance, date_str


def set_daily_start_balance(balance: float):
    today_utc = datetime.now(timezone.utc).date().isoformat()
    execute(
        "UPDATE system_state SET value=%s, updated_at=NOW() WHERE key='daily_start_balance'",
        (str(balance),),
    )
    execute(
        "UPDATE system_state SET value=%s, updated_at=NOW() WHERE key='daily_start_date'",
        (today_utc,),
    )
