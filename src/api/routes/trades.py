from fastapi import APIRouter
from src.db import execute

router = APIRouter()


@router.get("/trades")
def get_trades(limit: int = 50):
    try:
        rows = execute(
            """SELECT open_time, close_time, direction, lot_size,
                      open_price, close_price, sl, tp, pnl, result
               FROM trades ORDER BY close_time DESC LIMIT %s""",
            (limit,), fetch=True,
        )
    except Exception:
        return {"error": "Database unavailable"}
    data = [
        {
            "open_time": str(r[0]), "close_time": str(r[1]), "direction": r[2],
            "lot_size": r[3], "open_price": r[4], "close_price": r[5],
            "sl": r[6], "tp": r[7], "pnl": r[8], "result": r[9],
        }
        for r in (rows or [])
    ]
    return {"data": data}
