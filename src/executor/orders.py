import logging
import MetaTrader5 as mt5
from src.mt5_bridge.data import SYMBOL

logger = logging.getLogger(__name__)


def place_order(direction: str, lot_size: float, sl: float, tp: float) -> dict:
    """Place a market order. Returns dict with success bool and ticket/error."""
    order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        return {"success": False, "retcode": None, "comment": "no tick data"}
    price = tick.ask if direction == "BUY" else tick.bid
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": lot_size,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 20260325,
        "comment": "opengold",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        retcode = result.retcode if result else "None"
        comment = result.comment if result else "no result"
        logger.error(f"ORDER_REJECTED: retcode={retcode} comment={comment}")
        return {"success": False, "retcode": retcode, "comment": comment}
    logger.info(f"Order placed: {direction} {lot_size} lots ticket={result.order}")
    return {"success": True, "ticket": result.order, "price": result.price}


def sync_positions(previous_snapshot: list[dict], positions_get_fn) -> tuple[list[dict], list[dict]]:
    """Compare snapshots to find closed positions.

    Returns (closed_positions, current_positions).
    """
    current = positions_get_fn()
    current_tickets = {p["ticket"] for p in current}
    closed = [p for p in previous_snapshot if p["ticket"] not in current_tickets]
    return closed, current
