import time
import logging
from datetime import datetime, timedelta, timezone

from src import config
from src.mt5_bridge.connection import connect, disconnect, is_connected, get_account_info
from src.mt5_bridge.data import fetch_candles, get_last_candle_time, get_positions, get_history_deals
from src.regime.classifier import classify
from src.strategies import run_all
from src.aggregator.scorer import aggregate
from src.trigger.gate import should_trigger, get_direction
from src.risk.engine import validate
from src.executor.orders import place_order, sync_positions
from src.logger.writer import (
    log_decision, log_trade,
    get_kill_switch_state, set_kill_switch,
    get_daily_start_balance, set_daily_start_balance,
    check_and_log_trade_no_duplicate,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("main")


def connect_with_retry(retries: int = 3) -> bool:
    for attempt in range(retries):
        if connect():
            return True
        wait = 2 ** (attempt + 1)   # 2s, 4s, 8s
        logger.warning(f"MT5 connect attempt {attempt + 1} failed — retrying in {wait}s")
        time.sleep(wait)
    return False


def _check_daily_reset(balance: float):
    """Refresh daily_start_balance at each UTC midnight."""
    today_utc = datetime.now(timezone.utc).date().isoformat()
    _, stored_date = get_daily_start_balance()
    if stored_date != today_utc:
        set_daily_start_balance(balance)
        logger.info(f"Daily start balance reset for {today_utc}: {balance}")


def _reconcile_missed_closes():
    """After reconnect, pull last-hour deals from MT5 history and log any missed closes."""
    now = datetime.now(timezone.utc)
    deals = get_history_deals(now - timedelta(hours=1), now)
    for deal in deals:
        if deal["entry"] == 1:   # 1 = OUT (closing deal)
            # MT5 deal type: 0=BUY deal (closes a SELL position), 1=SELL deal (closes BUY position)
            original_direction = "SELL" if deal["type"] == 0 else "BUY"
            check_and_log_trade_no_duplicate(
                open_time=deal["time"],
                close_time=deal["time"],
                direction=original_direction,
                lot_size=deal["volume"],
                open_price=deal["price"],
                close_price=deal["price"],
                sl=0.0,
                tp=0.0,
                pnl=deal["profit"],
            )


def main():
    logger.info("OpenGold starting…")
    if not connect_with_retry():
        logger.critical("Cannot connect to MT5 after retries. Exiting.")
        return

    last_candle_time = None
    position_snapshot: list[dict] = []

    while True:
        try:
            # ── Reconnect check ───────────────────────────────────────────
            if not is_connected():
                logger.warning("MT5 disconnected — reconnecting…")
                if not connect_with_retry():
                    logger.error("Reconnect failed. Pausing 60s.")
                    time.sleep(60)
                    continue
                _reconcile_missed_closes()

            # ── Poll for new candle ───────────────────────────────────────
            current_time = get_last_candle_time()
            if current_time is None or current_time == last_candle_time:
                time.sleep(config.POLL_INTERVAL_SECONDS)
                continue

            last_candle_time = current_time
            candles = fetch_candles(200)
            if candles.empty:
                time.sleep(config.POLL_INTERVAL_SECONDS)
                continue

            # ── Account state ─────────────────────────────────────────────
            account = get_account_info()
            balance = account.get("balance", 0.0)
            equity = account.get("equity", 0.0)
            _check_daily_reset(balance)

            # ── Drawdown kill switch ──────────────────────────────────────
            kill_switch = get_kill_switch_state()
            daily_start, _ = get_daily_start_balance()
            if daily_start > 0 and equity < daily_start * (1 - config.DAILY_DRAWDOWN_LIMIT):
                if not kill_switch:
                    logger.warning(
                        f"KILL SWITCH ACTIVATED: equity={equity:.2f} start={daily_start:.2f}"
                    )
                    set_kill_switch(True)
                    kill_switch = True

            # ── Position sync (detect closed trades) ─────────────────────
            closed_positions, position_snapshot = sync_positions(position_snapshot, get_positions)
            for closed in closed_positions:
                log_trade(
                    open_time=datetime.now(timezone.utc),
                    close_time=datetime.now(timezone.utc),
                    direction=closed["direction"],
                    lot_size=closed["volume"],
                    open_price=closed["open_price"],
                    close_price=candles["close"].iloc[-1],
                    sl=closed["sl"],
                    tp=closed["tp"],
                    pnl=0.0,   # placeholder — real PnL reconciled via MT5 history in Phase 3
                )

            # ── Strategy pipeline ─────────────────────────────────────────
            regime = classify(candles)
            signals = run_all(candles, regime)
            agg = aggregate(signals, regime)
            open_trades = len(position_snapshot)
            triggered = should_trigger(agg, open_trades, kill_switch)

            logger.info(
                f"Candle {current_time} | regime={regime} | "
                f"buy={agg.buy_score:.2f} sell={agg.sell_score:.2f} | "
                f"trigger={'YES' if triggered else 'NO'} | open_trades={open_trades}"
            )

            if not triggered:
                log_decision(regime, agg.buy_score, agg.sell_score, trigger_fired=False)
                time.sleep(config.POLL_INTERVAL_SECONDS)
                continue

            # ── Phase 1: direction from scores, fixed confidence, ATR-based SL/TP ──
            direction = get_direction(agg)
            price = candles["close"].iloc[-1]
            atr_range = (
                candles["high"].rolling(14).max() - candles["low"].rolling(14).min()
            ).iloc[-1]
            if direction == "BUY":
                sl = price - atr_range * 1.5
                tp = price + atr_range * 2.0
            else:
                sl = price + atr_range * 1.5
                tp = price - atr_range * 2.0
            confidence = 0.75   # fixed in Phase 1; replaced by AI confidence in Phase 3

            risk = validate(
                action=direction,
                confidence=confidence,
                sl=sl,
                tp=tp,
                entry=price,
                balance=balance,
                open_trades=open_trades,
                kill_switch=kill_switch,
            )

            if not risk.approved:
                logger.info(f"Risk blocked: {risk.block_reason}")
                log_decision(
                    regime, agg.buy_score, agg.sell_score, trigger_fired=True,
                    ai_action=direction, ai_confidence=confidence,
                    ai_sl=sl, ai_tp=tp, risk_block_reason=risk.block_reason,
                )
                time.sleep(config.POLL_INTERVAL_SECONDS)
                continue

            order = place_order(direction, risk.lot_size, sl, tp)
            log_decision(
                regime, agg.buy_score, agg.sell_score, trigger_fired=True,
                ai_action=direction, ai_confidence=confidence,
                ai_sl=sl, ai_tp=tp,
                risk_block_reason=None if order["success"] else "ORDER_REJECTED",
            )

        except KeyboardInterrupt:
            logger.info("Shutting down on KeyboardInterrupt…")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
            time.sleep(config.POLL_INTERVAL_SECONDS)

    disconnect()
    logger.info("OpenGold stopped.")


if __name__ == "__main__":
    main()
