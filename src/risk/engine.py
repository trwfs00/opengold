from dataclasses import dataclass
from src import config

MIN_LOT = 0.01
LOT_STEP = 0.01


@dataclass
class RiskResult:
    approved: bool
    lot_size: float = 0.0
    block_reason: str | None = None


def validate(
    action: str,
    confidence: float,
    sl: float,
    tp: float,
    entry: float,
    balance: float,
    open_trades: int,
    kill_switch: bool,
    daily_trade_count: int = 0,
    daily_start_balance: float = 0.0,
    equity: float = 0.0,
) -> RiskResult:
    if kill_switch:
        return RiskResult(approved=False, block_reason="KILL_SWITCH_ACTIVE")
    if open_trades >= config.MAX_CONCURRENT_TRADES:
        return RiskResult(approved=False, block_reason="MAX_TRADES_REACHED")
    if daily_trade_count >= config.MAX_TRADES_PER_DAY:
        return RiskResult(approved=False, block_reason="DAILY_TRADE_LIMIT")
    if daily_start_balance > 0 and equity < daily_start_balance * (1 - config.DAILY_DRAWDOWN_LIMIT):
        return RiskResult(approved=False, block_reason="DAILY_DRAWDOWN")
    if confidence < config.MIN_AI_CONFIDENCE:
        return RiskResult(approved=False, block_reason="LOW_CONFIDENCE")

    sl_distance = abs(entry - sl)
    risk_amount = balance * config.RISK_PER_TRADE

    if config.CONTRACT_SIZE >= 100_000:  # Forex pair
        pip_size = 0.01 if "JPY" in config.SYMBOL else 0.0001
        sl_pips = sl_distance / pip_size
        tp_pips = abs(tp - entry) / pip_size
        if not (config.SL_PIPS_MIN <= sl_pips <= config.SL_PIPS_MAX):
            return RiskResult(approved=False, block_reason="INVALID_SL")
        if tp_pips < config.SL_PIPS_MIN * config.MIN_RR_RATIO:
            return RiskResult(approved=False, block_reason="INVALID_TP")
        lot_size = risk_amount / (sl_pips * config.PIP_VALUE_PER_LOT)
    else:  # Gold / commodities: 1 lot = CONTRACT_SIZE oz
        if sl_distance < config.MIN_SL_USD or sl_distance > config.MAX_SL_USD:
            return RiskResult(approved=False, block_reason="INVALID_SL")
        tp_distance = abs(tp - entry)
        if tp_distance < config.MIN_TP_USD:
            return RiskResult(approved=False, block_reason="INVALID_TP")
        if sl_distance > 0 and (tp_distance / sl_distance) < config.MIN_RR_RATIO:
            return RiskResult(approved=False, block_reason="LOW_RR_RATIO")
        # Note: config.CONTRACT_SIZE replaces the old hardcoded 100 — default is 100 (Gold)
        lot_size = risk_amount / (sl_distance * config.CONTRACT_SIZE)

    lot_size = (lot_size // LOT_STEP) * LOT_STEP
    if lot_size < MIN_LOT:
        return RiskResult(approved=False, block_reason="BELOW_MIN_LOT")

    return RiskResult(approved=True, lot_size=round(lot_size, 2))
