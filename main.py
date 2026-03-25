import time
import logging
from datetime import datetime, timedelta, timezone

from src import config
from src.mt5_bridge.connection import connect, disconnect, is_connected, get_account_info
from src.mt5_bridge.data import fetch_candles, get_last_candle_time, get_positions, get_history_deals
from src.regime.classifier import classify as classify_regime
from src.strategies import run_all
from src.aggregator.scorer import aggregate as compute_agg
from src.trigger.gate import should_trigger
from src.risk.engine import validate
from src.executor.orders import place_order, sync_positions
from src.logger.writer import (
    log_decision, log_trade,
    get_kill_switch_state, set_kill_switch,
    get_daily_start_balance, set_daily_start_balance,
    check_and_log_trade_no_duplicate,
)
from src.journal.reader import get_journal_context
from src.ai_layer.prompt import build_prompt
from src.ai_layer.client import decide

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("main")


def connect_with_retry(retries: int = 3) -> bool:
    for attempt in range(retries):
        if connect():
            return True
        if attempt < retries - 1:
            wait = config.MT5_RECONNECT_DELAY_BASE ** (attempt + 1)
            logger.warning(f"MT5 connect attempt {attempt + 1} failed — retrying in {wait}s")
            time.sleep(wait)
        else:
            logger.warning(f"MT5 connect attempt {attempt + 1} failed — no more retries")
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



def get_open_trades() -> int:
    """Return the number of currently open trades."""
    return len(get_positions())


def kill_switch_active() -> bool:
    """Return the current kill-switch state."""
    return get_kill_switch_state()


def run_loop():
    """Core strategy loop. Polls for new candles and makes trading decisions."""
    last_candle_time = None
    while True:
        try:
            candles = fetch_candles(200)
            if candles.empty:
                time.sleep(config.POLL_INTERVAL_SECONDS)
                continue

            new_time = candles["time"].iloc[-1]
            if new_time == last_candle_time:
                time.sleep(config.POLL_INTERVAL_SECONDS)
                continue
            last_candle_time = new_time

            open_trades = get_open_trades()
            kill = kill_switch_active()

            regime = classify_regime(candles)
            signals = run_all(candles, regime)
            agg = compute_agg(signals, regime)
            triggered = should_trigger(agg, open_trades, kill)

            logger.info(
                f"Candle {new_time} | regime={regime} | "
                f"buy={agg.buy_score:.2f} sell={agg.sell_score:.2f} | "
                f"trigger={'YES' if triggered else 'NO'} | open_trades={open_trades}"
            )

            if not triggered:
                log_decision(regime, agg.buy_score, agg.sell_score, trigger_fired=False)
                time.sleep(config.POLL_INTERVAL_SECONDS)
                continue

            # ── Phase 3: journal → AI → risk ─────────────────────────────────────
            price = candles["close"].iloc[-1]
            atr = (candles["high"].rolling(14).max() - candles["low"].rolling(14).min()).iloc[-1]
            journal = get_journal_context()
            ai_prompt = build_prompt(
                journal=journal,
                regime=regime,
                buy_score=agg.buy_score,
                sell_score=agg.sell_score,
                price=price,
                atr=atr,
            )
            ai = decide(ai_prompt)
            if ai.action == "SKIP" or ai.error:
                log_decision(
                    regime, agg.buy_score, agg.sell_score, trigger_fired=True,
                    ai_action="SKIP", risk_block_reason=ai.error or "AI_SKIP",
                )
                time.sleep(config.POLL_INTERVAL_SECONDS)
                continue
            direction = ai.action
            confidence = ai.confidence
            sl = ai.sl
            tp = ai.tp

            account = get_account_info()
            balance = account.get("balance", 0.0)

            risk = validate(
                action=direction,
                confidence=confidence,
                sl=sl,
                tp=tp,
                entry=price,
                balance=balance,
                open_trades=open_trades,
                kill_switch=kill,
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
            time.sleep(config.POLL_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            logger.info("Shutting down on KeyboardInterrupt…")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
            time.sleep(config.POLL_INTERVAL_SECONDS)

    disconnect()
    logger.info("OpenGold stopped.")


def main():
    logger.info("OpenGold starting…")
    if not connect_with_retry():
        logger.critical("Cannot connect to MT5 after retries. Exiting.")
        return
    run_loop()


if __name__ == "__main__":
    main()
