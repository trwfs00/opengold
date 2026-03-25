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
) -> RiskResult:
    if kill_switch:
        return RiskResult(approved=False, block_reason="KILL_SWITCH_ACTIVE")
    if open_trades >= config.MAX_CONCURRENT_TRADES:
        return RiskResult(approved=False, block_reason="MAX_TRADES_REACHED")
    if confidence < config.MIN_AI_CONFIDENCE:
        return RiskResult(approved=False, block_reason="LOW_CONFIDENCE")

    sl_distance = abs(entry - sl)
    if sl_distance < config.MIN_SL_USD or sl_distance > config.MAX_SL_USD:
        return RiskResult(approved=False, block_reason="INVALID_SL")

    # lot = (balance × risk%) / (sl_distance_usd × 100 oz/lot)
    risk_amount = balance * config.RISK_PER_TRADE
    lot_size = risk_amount / (sl_distance * 100)
    # Round down to nearest LOT_STEP
    lot_size = (lot_size // LOT_STEP) * LOT_STEP

    if lot_size < MIN_LOT:
        return RiskResult(approved=False, block_reason="BELOW_MIN_LOT")

    return RiskResult(approved=True, lot_size=round(lot_size, 2))
