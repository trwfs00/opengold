from fastapi import APIRouter, Query
from src.db import execute

router = APIRouter()


@router.get("/position-events")
def get_position_events(limit: int = Query(default=200, le=2000)):
    try:
        rows = execute(
            """SELECT id, time, ticket, event_type, direction,
                      old_sl, new_sl, price, reasoning
               FROM position_events
               ORDER BY time DESC LIMIT %s""",
            (limit,), fetch=True,
        )
    except Exception:
        return {"error": "Database unavailable"}
    data = [
        {
            "id": r[0],
            "time": str(r[1]),
            "ticket": r[2],
            "event_type": r[3],
            "direction": r[4],
            "old_sl": r[5],
            "new_sl": r[6],
            "price": r[7],
            "reasoning": r[8],
        }
        for r in (rows or [])
    ]
    return {"data": data}
