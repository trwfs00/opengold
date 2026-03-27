"""Hybrid Position Manager — trailing stop + AI re-evaluation.

Called every candle tick from the main loop. For each open position:
1. Trailing stop: move SL to breakeven at BE_RATIO × TP distance
   (or when USD profit >= TRAIL_MIN_PROFIT_USD), then ATR-trail beyond.
2. AI re-evaluation: when strategies produce a strong counter-signal,
   ask Claude whether to HOLD or CLOSE the position.
"""

import math
import logging
from datetime import datetime, timezone
from src import config
from src.executor.orders import modify_sl, close_position, partial_close_position
from src.ai_layer.client import decide
from src.logger.writer import log_position_event

logger = logging.getLogger(__name__)

# Internal state: tracks which positions have reached breakeven
_be_reached: set[int] = set()
# Tracks last AI re-evaluation time per ticket
_last_reeval: dict[int, datetime] = {}
# Tracks positions that have already been partially closed (one partial per position)
_partial_closed: set[int] = set()


def _compute_atr(candles) -> float:
    """ATR(14) from candle DataFrame."""
    high = candles["high"]
    low = candles["low"]
    close = candles["close"]
    tr = (high - low).combine(
        (high - close.shift(1)).abs(), max
    ).combine(
        (low - close.shift(1)).abs(), max
    )
    return float(tr.rolling(config.ATR_LOOKBACK).mean().iloc[-1])


def _trail_sl(pos: dict, atr: float) -> tuple[float, str] | None:
    """Compute new SL for trailing. Returns (new_sl, event_type) or None if no move needed.

    Logic:
    - Phase 1 (pre-breakeven): once profit reaches the BE trigger threshold,
      move SL to entry (breakeven).
      Trigger is the earlier of:
        (a) profit >= TRAIL_BE_RATIO × TP distance  (TP-based)
        (b) unrealised PnL >= TRAIL_MIN_PROFIT_USD  (USD-based fallback,
            also catches positions with no TP set)
    - Phase 2 (post-breakeven): trail SL at price ∓ ATR × multiplier,
      but never move SL backwards.
    """
    ticket = pos["ticket"]
    direction = pos["direction"]
    entry = pos["open_price"]
    current = pos["current_price"]
    current_sl = pos["sl"]
    tp = pos["tp"]
    pnl = pos.get("unrealized_pnl", 0.0)

    profit_dist = (current - entry) if direction == "BUY" else (entry - current)
    if profit_dist <= 0:
        return None  # in loss, skip

    # --- Determine BE trigger distance (in price units) ---
    be_trigger: float | None = None
    if tp != 0:
        tp_dist = abs(tp - entry)
        if tp_dist > 0:
            be_trigger = tp_dist * config.TRAIL_BE_RATIO

    # USD-profit override: when unrealised PnL >= TRAIL_MIN_PROFIT_USD,
    # treat position as having reached breakeven regardless of TP.
    if config.TRAIL_MIN_PROFIT_USD > 0 and pnl >= config.TRAIL_MIN_PROFIT_USD:
        # Force immediate BE: set trigger to 0 so any positive profit qualifies.
        be_trigger = 0.0

    if be_trigger is None:
        # No TP set and TRAIL_MIN_PROFIT_USD not configured / not yet reached.
        return None

    # --- Phase 1: Move SL to breakeven ---
    if ticket not in _be_reached:
        if profit_dist < be_trigger:
            return None  # trigger not yet reached
        _be_reached.add(ticket)
        if direction == "BUY":
            if current_sl < entry:
                logger.info(f"Trail BE: ticket={ticket} moving SL to entry {entry}")
                return (entry, "TRAIL_BE")
        else:
            if current_sl > entry or current_sl == 0:
                logger.info(f"Trail BE: ticket={ticket} moving SL to entry {entry}")
                return (entry, "TRAIL_BE")
        # SL already at/beyond entry — fall straight into Phase 2 this tick.

    # --- Phase 2: ATR-based trail ---
    if math.isnan(atr) or atr <= 0:
        logger.warning(f"Trail: ATR invalid ({atr}) for ticket={ticket}, skipping Phase 2")
        return None

    if direction == "BUY":
        trail_sl = round(current - atr * config.TRAIL_ATR_MULTIPLIER, 5)
        if trail_sl > current_sl:
            return (trail_sl, "TRAIL_SL")
    else:
        trail_sl = round(current + atr * config.TRAIL_ATR_MULTIPLIER, 5)
        if trail_sl < current_sl or current_sl == 0:
            return (trail_sl, "TRAIL_SL")

    return None


def _should_reeval(pos: dict, buy_score: float, sell_score: float) -> bool:
    """Check if a position warrants AI re-evaluation.

    True when: strategies produce a strong counter-signal AND enough time
    has passed since the last re-evaluation for this ticket.
    """
    if config.REEVAL_INTERVAL_MINUTES <= 0:
        return False

    ticket = pos["ticket"]
    direction = pos["direction"]

    # Counter-signal: strong sell when holding BUY, strong buy when holding SELL
    counter = sell_score if direction == "BUY" else buy_score
    if counter < config.REEVAL_MIN_COUNTER_SCORE:
        return False

    now = datetime.now(timezone.utc)
    last = _last_reeval.get(ticket)
    if last and (now - last).total_seconds() < config.REEVAL_INTERVAL_MINUTES * 60:
        return False

    return True


def _build_reeval_prompt(pos: dict, regime: str, buy_score: float,
                         sell_score: float, atr: float) -> str:
    """Build a focused prompt for Claude to decide HOLD / PARTIAL_CLOSE / CLOSE."""
    direction = pos["direction"]
    entry = pos["open_price"]
    current = pos["current_price"]
    pnl = pos["unrealized_pnl"]
    sl = pos["sl"]
    tp = pos["tp"]
    lots = pos.get("lots", 0)
    already_partial = pos["ticket"] in _partial_closed
    partial_note = " (already partially closed, only HOLD or CLOSE allowed)" if already_partial else ""
    actions = '"HOLD"|"CLOSE"' if already_partial else '"HOLD"|"PARTIAL_CLOSE"|"CLOSE"'
    partial_desc = (
        f"PARTIAL_CLOSE = lock in {int(config.PARTIAL_CLOSE_RATIO * 100)}% profit now, "
        f"let the rest run with trailing stop.\n"
    ) if not already_partial else ""

    return (
        f"[OPEN POSITION]{partial_note}\n"
        f"Direction: {direction} | Entry: {entry} | Current: {current} | "
        f"Unrealised PnL: {pnl:+.2f} | Lots: {lots}\n"
        f"SL: {sl} | TP: {tp}\n\n"
        f"[MARKET]\n"
        f"Regime: {regime} | Buy score: {buy_score:.1f} | Sell score: {sell_score:.1f} | "
        f"ATR: {atr:.5f}\n\n"
        f"[TASK]\n"
        f"You are managing this open {direction} position. "
        f"The strategies are now signalling against this trade "
        f"(counter-score: {sell_score if direction == 'BUY' else buy_score:.1f}).\n"
        f"{partial_desc}"
        f"Reply with ONLY valid JSON:\n"
        f'{{"action": {actions}, '
        f'"reasoning": "<one sentence>"}}'
    )


def manage_positions(positions: list[dict], candles, regime: str,
                     buy_score: float, sell_score: float) -> None:
    """Called every candle tick. Trails stops and triggers AI re-evaluation."""
    if not positions:
        return

    atr = _compute_atr(candles)

    # Clean up state for positions that no longer exist
    active_tickets = {p["ticket"] for p in positions}
    for t in list(_be_reached):
        if t not in active_tickets:
            _be_reached.discard(t)
    for t in list(_last_reeval):
        if t not in active_tickets:
            del _last_reeval[t]
    for t in list(_partial_closed):
        if t not in active_tickets:
            _partial_closed.discard(t)

    for pos in positions:
        ticket = pos["ticket"]

        # ── Trailing Stop ──────────────────────────────────────────
        if config.TRAIL_ENABLED:
            trail_result = _trail_sl(pos, atr)
            if trail_result is not None:
                new_sl, event_type = trail_result
                new_sl = round(new_sl, 5)
                logger.info(
                    f"Trail: ticket={ticket} {pos['direction']} "
                    f"SL {pos['sl']} → {new_sl} [{event_type}]"
                )
                modify_sl(ticket, new_sl, dry_run=config.DRY_RUN)
                log_position_event(
                    ticket=ticket,
                    event_type=event_type,
                    direction=pos["direction"],
                    price=pos["current_price"],
                    old_sl=pos["sl"],
                    new_sl=new_sl,
                )

        # ── AI Re-evaluation ───────────────────────────────────────
        if _should_reeval(pos, buy_score, sell_score):
            logger.info(
                f"Re-eval triggered: ticket={ticket} {pos['direction']} "
                f"counter={sell_score if pos['direction'] == 'BUY' else buy_score:.1f}"
            )
            _last_reeval[ticket] = datetime.now(timezone.utc)
            prompt = _build_reeval_prompt(pos, regime, buy_score, sell_score, atr)
            ai = decide(prompt)
            if ai.action == "CLOSE":
                logger.info(
                    f"AI says CLOSE ticket={ticket}: {ai.reasoning}"
                )
                log_position_event(
                    ticket=ticket,
                    event_type="REEVAL_CLOSE",
                    direction=pos["direction"],
                    price=pos["current_price"],
                    old_sl=pos["sl"],
                    reasoning=ai.reasoning,
                )
                close_position(ticket, dry_run=config.DRY_RUN)
            elif ai.action == "PARTIAL_CLOSE" and ticket not in _partial_closed:
                close_lots = round(pos.get("lots", 0) * config.PARTIAL_CLOSE_RATIO, 2)
                logger.info(
                    f"AI says PARTIAL_CLOSE ticket={ticket} lots={close_lots}: {ai.reasoning}"
                )
                log_position_event(
                    ticket=ticket,
                    event_type="PARTIAL_CLOSE",
                    direction=pos["direction"],
                    price=pos["current_price"],
                    old_sl=pos["sl"],
                    reasoning=ai.reasoning,
                )
                if partial_close_position(ticket, close_lots, dry_run=config.DRY_RUN):
                    _partial_closed.add(ticket)
            else:
                logger.info(
                    f"AI says HOLD ticket={ticket}: {ai.reasoning}"
                )
                log_position_event(
                    ticket=ticket,
                    event_type="REEVAL_HOLD",
                    direction=pos["direction"],
                    price=pos["current_price"],
                    old_sl=pos["sl"],
                    reasoning=ai.reasoning,
                )
