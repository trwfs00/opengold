from fastapi import APIRouter
from src.db import execute

router = APIRouter()


@router.get("/decisions")
def get_decisions(limit: int = 50):
    try:
        rows = execute(
            """SELECT time, regime, buy_score, sell_score, trigger_fired,
                      ai_action, ai_confidence, ai_sl, ai_tp, risk_block_reason
               FROM decisions ORDER BY time DESC LIMIT %s""",
            (limit,), fetch=True,
        )
    except Exception:
        return {"error": "Database unavailable"}
    data = [
        {
            "time": str(r[0]), "regime": r[1], "buy_score": r[2], "sell_score": r[3],
            "trigger_fired": r[4], "ai_action": r[5], "ai_confidence": r[6],
            "ai_sl": r[7], "ai_tp": r[8], "risk_block_reason": r[9],
        }
        for r in (rows or [])
    ]
    return {"data": data}
