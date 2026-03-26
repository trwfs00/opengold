import time
import logging
import argparse
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

# ── Phase 1: parse --env flag and load profile BEFORE any src.* imports ──────
# (config.py reads os.environ at import time; dotenv must run first)
_env_parser = argparse.ArgumentParser(add_help=False)
_env_parser.add_argument("--env", default=".env",
                         help="ENV profile file (e.g. gold.env or forex.env)")
_env_args, _ = _env_parser.parse_known_args()
load_dotenv(_env_args.env, override=True)

# ── Phase 2: import src modules (they now see the correct env values) ─────────
from src import config
from src.mt5_bridge.connection import connect, disconnect, is_connected, get_account_info
from src.mt5_bridge.data import fetch_candles, get_last_candle_time, get_positions, get_history_deals
from src.regime.classifier import classify as classify_regime
from src.strategies import run_all
from src.aggregator.scorer import aggregate as compute_agg
from collections import Counter
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
from src.db import execute

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



def _log_closed_positions(closed: list[dict]):
    """Look up closing deals for each closed position and write to trades table."""
    now = datetime.now(timezone.utc)
    deals = get_history_deals(now - timedelta(hours=2), now)
    closing_deals = {d["order"]: d for d in deals if d["entry"] == 1}
    for pos in closed:
        deal = closing_deals.get(pos["ticket"])
        if deal is None:
            # Fallback: use position snapshot data
            check_and_log_trade_no_duplicate(
                open_time=datetime.fromisoformat(pos["open_time"]),
                close_time=now,
                direction=pos["direction"],
                lot_size=pos["lots"],
                open_price=pos["open_price"],
                close_price=pos["current_price"],
                sl=pos.get("sl", 0.0),
                tp=pos.get("tp", 0.0),
                pnl=pos["unrealized_pnl"],
            )
        else:
            check_and_log_trade_no_duplicate(
                open_time=datetime.fromisoformat(pos["open_time"]),
                close_time=deal["time"],
                direction=pos["direction"],
                lot_size=deal["volume"],
                open_price=pos["open_price"],
                close_price=deal["price"],
                sl=pos.get("sl", 0.0),
                tp=pos.get("tp", 0.0),
                pnl=deal["profit"],
            )
        logger.info(f"Logged closed trade: {pos['direction']} ticket={pos['ticket']}")


def run_loop():
    """Core strategy loop. Polls for new candles and makes trading decisions."""
    last_candle_time = None
    position_snapshot: list[dict] = []
    last_ai_time: datetime | None = None
    score_buffer: list[dict] = []
    while True:
        try:
            candles = fetch_candles(200)
            if candles.empty:
                if not is_connected():
                    logger.warning("MT5 connection lost — attempting reconnect")
                    if connect_with_retry(config.MT5_RECONNECT_RETRIES):
                        logger.info("Reconnected — reconciling missed closes")
                        _reconcile_missed_closes()
                    else:
                        logger.error("Reconnect failed — will retry next candle")
                # If is_connected() is True but candles are still empty (market closed,
                # weekend, holiday), the reconnect block is skipped — intentional.
                time.sleep(config.POLL_INTERVAL_SECONDS)
                continue

            new_time = candles["time"].iloc[-1]
            if new_time == last_candle_time:
                time.sleep(config.POLL_INTERVAL_SECONDS)
                continue
            last_candle_time = new_time

            # ── Detect closed positions since last tick ───────────────────────
            closed_positions, position_snapshot = sync_positions(position_snapshot, get_positions)
            if closed_positions:
                logger.info(f"Detected {len(closed_positions)} closed position(s) — logging trades")
                _log_closed_positions(closed_positions)

            open_trades = len(position_snapshot)
            kill = get_kill_switch_state()

            regime = classify_regime(candles)
            signals = run_all(candles, regime)
            agg = compute_agg(signals, regime)

            # Accumulate rolling score window
            score_buffer.append({"buy": agg.buy_score, "sell": agg.sell_score, "regime": regime})
            if len(score_buffer) > config.AI_INTERVAL_MINUTES:
                score_buffer.pop(0)

            now_utc = datetime.now(timezone.utc)
            ai_interval_s = config.AI_INTERVAL_MINUTES * 60
            eligible = not kill and open_trades < config.MAX_CONCURRENT_TRADES

            # Hot path: strong signal on this candle → skip wait
            hot_signal = (
                eligible
                and max(agg.buy_score, agg.sell_score) >= config.TRIGGER_MIN_SCORE
                and abs(agg.buy_score - agg.sell_score) >= config.TRIGGER_MIN_SCORE_DIFF
                and (last_ai_time is None or (now_utc - last_ai_time).total_seconds() >= 60)
            )
            # Periodic path: 5-min window elapsed
            periodic = (
                eligible
                and len(score_buffer) >= 2
                and (last_ai_time is None or (now_utc - last_ai_time).total_seconds() >= ai_interval_s)
            )
            ai_ready = hot_signal or periodic
            ai_trigger = "HOT" if hot_signal else ("PERIODIC" if periodic else "WAIT")

            logger.info(
                f"Candle {new_time} | regime={regime} | "
                f"buy={agg.buy_score:.2f} sell={agg.sell_score:.2f} | "
                f"ai={ai_trigger} | open_trades={open_trades}"
            )

            if not ai_ready:
                log_decision(regime, agg.buy_score, agg.sell_score, trigger_fired=False, signals=agg.signals)
                time.sleep(config.POLL_INTERVAL_SECONDS)
                continue

            last_ai_time = now_utc

            # Compute 5-min window statistics for Claude
            window_size = len(score_buffer)
            dominant_regime = Counter(s["regime"] for s in score_buffer).most_common(1)[0][0]
            buy_avg  = sum(s["buy"]  for s in score_buffer) / window_size
            sell_avg = sum(s["sell"] for s in score_buffer) / window_size
            buy_peak  = max(s["buy"]  for s in score_buffer)
            sell_peak = max(s["sell"] for s in score_buffer)

            # ── Phase 3: journal → AI → risk ─────────────────────────────────────
            price = candles["close"].iloc[-1]
            atr = (candles["high"].rolling(14).max() - candles["low"].rolling(14).min()).iloc[-1]
            journal = get_journal_context()
            ai_prompt = build_prompt(
                journal=journal,
                regime=dominant_regime,
                buy_avg=buy_avg,
                sell_avg=sell_avg,
                buy_peak=buy_peak,
                sell_peak=sell_peak,
                window_minutes=window_size,
                price=price,
                atr=atr,
            )
            ai = decide(ai_prompt)
            if ai.action == "SKIP" or ai.error:
                log_decision(
                    regime, agg.buy_score, agg.sell_score, trigger_fired=True,
                    ai_action="SKIP", risk_block_reason=ai.error or "AI_SKIP",
                    signals=agg.signals, ai_reasoning=ai.reasoning,
                )
                time.sleep(config.POLL_INTERVAL_SECONDS)
                continue
            direction = ai.action
            confidence = ai.confidence
            sl = ai.sl
            tp = ai.tp

            account = get_account_info()
            balance = account.get("balance", 0.0)

            # Query today's placed trades for MAX_TRADES_PER_DAY gate
            try:
                rows = execute(
                    "SELECT COUNT(*) FROM trades "
                    "WHERE DATE(open_time AT TIME ZONE 'UTC') = current_date",
                    fetch=True,
                )
                daily_trade_count = int(rows[0][0]) if rows else 0
            except Exception:
                daily_trade_count = 0  # be permissive on DB error

            risk = validate(
                action=direction,
                confidence=confidence,
                sl=sl,
                tp=tp,
                entry=price,
                balance=balance,
                open_trades=open_trades,
                kill_switch=kill,
                daily_trade_count=daily_trade_count,
            )

            if not risk.approved:
                logger.info(f"Risk blocked: {risk.block_reason}")
                log_decision(
                    regime, agg.buy_score, agg.sell_score, trigger_fired=True,
                    ai_action=direction, ai_confidence=confidence,
                    ai_sl=sl, ai_tp=tp, risk_block_reason=risk.block_reason,
                    signals=agg.signals, ai_reasoning=ai.reasoning,
                )
                time.sleep(config.POLL_INTERVAL_SECONDS)
                continue

            order = place_order(direction, risk.lot_size, sl, tp, dry_run=config.DRY_RUN)
            log_decision(
                regime, agg.buy_score, agg.sell_score, trigger_fired=True,
                ai_action=direction, ai_confidence=confidence,
                ai_sl=sl, ai_tp=tp,
                risk_block_reason=None if order["success"] else "ORDER_REJECTED",
                signals=agg.signals, ai_reasoning=ai.reasoning,
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
    parser = argparse.ArgumentParser(description="OpenGold/OpenForex trading bot")
    parser.add_argument("--env", default=".env",
                        help="ENV profile file (e.g. gold.env or forex.env)")
    args = parser.parse_args()
    logger.info(f"Bot starting… [profile={args.env}] [symbol={config.SYMBOL}] [db={config.DB_NAME}]")
    if not connect_with_retry(config.MT5_RECONNECT_RETRIES):
        logger.critical("Cannot connect to MT5 after retries. Exiting.")
        return
    if config.DRY_RUN:
        logger.warning("*** DRY_RUN MODE — orders will NOT be sent to MT5 ***")
    run_loop()


if __name__ == "__main__":
    main()
