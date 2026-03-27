from fastapi import APIRouter
from src.db import execute

router = APIRouter()


@router.get("/summary")
def get_summary():
    try:
        today_decisions = execute(
            "SELECT trigger_fired, ai_action FROM decisions WHERE time::date = CURRENT_DATE",
            fetch=True,
        )
        all_time = execute("SELECT COUNT(*) FROM decisions", fetch=True)
        held = execute(
            "SELECT COUNT(*) FROM decisions WHERE NOT trigger_fired",
            fetch=True,
        )
        confluence = execute(
            "SELECT AVG(GREATEST(buy_score, sell_score)) FROM decisions",
            fetch=True,
        )
    except Exception:
        return {"error": "Database unavailable"}

    today_buy  = sum(1 for r in (today_decisions or []) if r[1] == "BUY")
    today_sell = sum(1 for r in (today_decisions or []) if r[1] == "SELL")
    today_hold = sum(1 for r in (today_decisions or []) if not r[0])

    total_dec = int((all_time or [[0]])[0][0] or 0)
    held_count = int((held or [[0]])[0][0] or 0)
    hold_rate = (held_count / total_dec) if total_dec else None

    conf_raw = (confluence or [[None]])[0][0]
    conf_avg = round(float(conf_raw), 2) if conf_raw is not None else None

    return {
        "today_buy": today_buy,
        "today_sell": today_sell,
        "today_hold": today_hold,
        "all_time_decisions": total_dec,
        "discipline_hold_rate": round(float(hold_rate), 4) if hold_rate is not None else None,
        "confluence_avg": conf_avg,
    }
