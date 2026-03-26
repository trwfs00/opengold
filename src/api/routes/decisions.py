from fastapi import APIRouter, Query
from typing import Optional
from src.db import execute

router = APIRouter()


@router.get("/decisions")
def get_decisions(
    limit: int = Query(default=1000, le=10000),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    try:
        conditions: list[str] = []
        params: list = []
        if date_from:
            conditions.append("time::date >= %s::date")
            params.append(date_from)
        if date_to:
            conditions.append("time::date <= %s::date")
            params.append(date_to)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)
        rows = execute(
            f"""SELECT time, regime, buy_score, sell_score, trigger_fired,
                      ai_action, ai_confidence, ai_sl, ai_tp, risk_block_reason, ai_reasoning
               FROM decisions {where} ORDER BY time DESC LIMIT %s""",
            tuple(params), fetch=True,
        )
    except Exception:
        return {"error": "Database unavailable"}
    data = [
        {
            "time": str(r[0]), "regime": r[1], "buy_score": r[2], "sell_score": r[3],
            "trigger_fired": r[4], "ai_action": r[5], "ai_confidence": r[6],
            "ai_sl": r[7], "ai_tp": r[8], "risk_block_reason": r[9],
            "ai_reasoning": r[10],
        }
        for r in (rows or [])
    ]
    return {"data": data}
