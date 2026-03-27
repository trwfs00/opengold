from fastapi import APIRouter
from datetime import datetime, timedelta, timezone

from src.mt5_bridge.data import get_history_deals
from src.logger.writer import check_and_log_trade_no_duplicate
from src.db import execute

router = APIRouter()


@router.post("/sync-trades")
def sync_trades(lookback_hours: int = 24):
    """Re-scan MT5 deal history and log any closing trades that were missed."""
    row = execute("SELECT COUNT(*) FROM trades", fetch=True)
    before = row[0][0] if row else 0

    now = datetime.now(timezone.utc)
    deals = get_history_deals(now - timedelta(hours=lookback_hours), now)
    for deal in deals:
        if deal["entry"] == 1 and abs(deal["profit"]) > 0.01:   # skip breakeven/zero-profit artifacts
            # MT5 type 0=BUY deal closes a SELL position; type 1=SELL deal closes a BUY position
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

    row = execute("SELECT COUNT(*) FROM trades", fetch=True)
    after = row[0][0] if row else 0

    return {"synced": after - before}
