from fastapi import APIRouter
from datetime import datetime, timedelta, timezone

from src.mt5_bridge.data import get_history_deals
from src.logger.writer import check_and_log_trade_no_duplicate
from src.db import execute

router = APIRouter()


@router.post("/sync-trades")
def sync_trades(lookback_hours: int = 24):
    """Re-scan MT5 deal history and log any closing trades that were missed.

    Pairs IN (entry=0) and OUT (entry=1) deals by position_id so open_time and
    open_price are taken from the opening deal — not the closing deal price.
    """
    row = execute("SELECT COUNT(*) FROM trades", fetch=True)
    before = row[0][0] if row else 0

    now = datetime.now(timezone.utc)
    all_deals = get_history_deals(now - timedelta(hours=lookback_hours), now)

    # Map position_id → opening deal (entry=0) for open_time / open_price
    in_deals = {d["position_id"]: d for d in all_deals if d["entry"] == 0}
    out_deals = [d for d in all_deals if d["entry"] == 1 and abs(d["profit"]) > 0.01]

    for deal in out_deals:
        # MT5 type 0=BUY deal closes a SELL position; type 1=SELL deal closes a BUY position
        original_direction = "SELL" if deal["type"] == 0 else "BUY"
        in_deal = in_deals.get(deal["position_id"])
        open_time = in_deal["time"] if in_deal else deal["time"]
        open_price = in_deal["price"] if in_deal else deal["price"]
        check_and_log_trade_no_duplicate(
            open_time=open_time,
            close_time=deal["time"],
            direction=original_direction,
            lot_size=deal["volume"],
            open_price=open_price,
            close_price=deal["price"],
            sl=0.0,
            tp=0.0,
            pnl=deal["profit"],
        )

    row = execute("SELECT COUNT(*) FROM trades", fetch=True)
    after = row[0][0] if row else 0

    return {"synced": after - before}
