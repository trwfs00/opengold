import logging
import MetaTrader5 as mt5
from src import config

logger = logging.getLogger(__name__)


def _filling_mode(symbol: str) -> int:
    """Return the first supported filling mode for the given symbol."""
    info = mt5.symbol_info(symbol)
    if info is None:
        return mt5.ORDER_FILLING_IOC
    filling_flags = info.filling_mode  # bitmask: 1=FOK, 2=IOC, 4=RETURN
    if filling_flags & 4:   # RETURN (most common for Demo / ECN brokers)
        return mt5.ORDER_FILLING_RETURN
    if filling_flags & 2:   # IOC
        return mt5.ORDER_FILLING_IOC
    return mt5.ORDER_FILLING_FOK  # fallback


def place_order(direction: str, lot_size: float, sl: float, tp: float, dry_run: bool = False) -> dict:
    """Place a market order. Returns dict with success bool and ticket/error."""
    if dry_run:
        logger.info(f"DRY_RUN order: {direction} {lot_size} lots sl={sl} tp={tp}")
        return {"success": True, "ticket": 0, "price": 0.0, "dry_run": True}
    order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
    tick = mt5.symbol_info_tick(config.SYMBOL)
    if tick is None:
        return {"success": False, "retcode": None, "comment": "no tick data"}
    price = tick.ask if direction == "BUY" else tick.bid
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": config.SYMBOL,
        "volume": lot_size,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 20260325,
        "comment": "opengold",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": _filling_mode(config.SYMBOL),
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


def modify_sl(ticket: int, new_sl: float, dry_run: bool = False) -> bool:
    """Move stop-loss on an open position. Returns True on success."""
    if dry_run:
        logger.info(f"DRY_RUN modify_sl: ticket={ticket} new_sl={new_sl}")
        return True
    pos = mt5.positions_get(ticket=ticket)
    if pos is None or len(pos) == 0:
        logger.warning(f"modify_sl: position {ticket} not found")
        return False
    p = pos[0]
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "symbol": p.symbol,
        "sl": new_sl,
        "tp": p.tp,
    }
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        retcode = result.retcode if result else "None"
        comment = result.comment if result else "no result"
        logger.error(f"modify_sl REJECTED: ticket={ticket} retcode={retcode} comment={comment}")
        return False
    logger.info(f"SL modified: ticket={ticket} new_sl={new_sl}")
    return True


def close_position(ticket: int, dry_run: bool = False) -> bool:
    """Market-close an open position. Returns True on success."""
    if dry_run:
        logger.info(f"DRY_RUN close_position: ticket={ticket}")
        return True
    pos = mt5.positions_get(ticket=ticket)
    if pos is None or len(pos) == 0:
        logger.warning(f"close_position: position {ticket} not found")
        return False
    p = pos[0]
    close_type = mt5.ORDER_TYPE_SELL if p.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    tick = mt5.symbol_info_tick(p.symbol)
    if tick is None:
        return False
    price = tick.bid if p.type == mt5.ORDER_TYPE_BUY else tick.ask
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": ticket,
        "symbol": p.symbol,
        "volume": p.volume,
        "type": close_type,
        "price": price,
        "deviation": 20,
        "magic": 20260325,
        "comment": "opengold_close",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": _filling_mode(p.symbol),
    }
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        retcode = result.retcode if result else "None"
        comment = result.comment if result else "no result"
        logger.error(f"close_position REJECTED: ticket={ticket} retcode={retcode} comment={comment}")
        return False
    logger.info(f"Position closed: ticket={ticket}")
    return True


def partial_close_position(ticket: int, close_lots: float, dry_run: bool = False) -> bool:
    """Partially close an open position by the given lot size.

    MT5 keeps the same ticket for the remaining portion.
    Returns True on success.
    """
    if dry_run:
        logger.info(f"DRY_RUN partial_close: ticket={ticket} close_lots={close_lots}")
        return True
    pos = mt5.positions_get(ticket=ticket)
    if pos is None or len(pos) == 0:
        logger.warning(f"partial_close: position {ticket} not found")
        return False
    p = pos[0]
    min_volume = mt5.symbol_info(p.symbol).volume_min if mt5.symbol_info(p.symbol) else 0.01
    close_lots = round(close_lots, 2)
    if close_lots < min_volume:
        logger.warning(
            f"partial_close: close_lots={close_lots} below min_volume={min_volume}, skipping"
        )
        return False
    if close_lots >= p.volume:
        # Lot to close >= full position — do full close instead
        return close_position(ticket, dry_run=dry_run)
    close_type = mt5.ORDER_TYPE_SELL if p.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    tick = mt5.symbol_info_tick(p.symbol)
    if tick is None:
        return False
    price = tick.bid if p.type == mt5.ORDER_TYPE_BUY else tick.ask
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": ticket,
        "symbol": p.symbol,
        "volume": close_lots,
        "type": close_type,
        "price": price,
        "deviation": 20,
        "magic": 20260325,
        "comment": "opengold_partial",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": _filling_mode(p.symbol),
    }
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        retcode = result.retcode if result else "None"
        comment = result.comment if result else "no result"
        logger.error(
            f"partial_close REJECTED: ticket={ticket} close_lots={close_lots} "
            f"retcode={retcode} comment={comment}"
        )
        return False
    logger.info(
        f"Partial close: ticket={ticket} closed={close_lots} "
        f"remaining={round(p.volume - close_lots, 2)}"
    )
    return True
