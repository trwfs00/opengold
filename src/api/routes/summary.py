from fastapi import APIRouter
from src.db import execute

router = APIRouter()


@router.get("/summary")
def get_summary():
    try:
        today_trades = execute(
            "SELECT result FROM trades WHERE close_time::date = CURRENT_DATE",
            fetch=True,
        )
        today_decisions = execute(
            "SELECT trigger_fired FROM decisions WHERE time::date = CURRENT_DATE",
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

    today_win = sum(1 for r in (today_trades or []) if r[0] == "WIN")
    today_loss = sum(1 for r in (today_trades or []) if r[0] == "LOSS")
    today_hold = sum(1 for r in (today_decisions or []) if not r[0])

    total_dec = int((all_time or [[0]])[0][0] or 0)
    held_count = int((held or [[0]])[0][0] or 0)
    hold_rate = (held_count / total_dec) if total_dec else None

    conf_raw = (confluence or [[None]])[0][0]
    conf_avg = round(float(conf_raw), 2) if conf_raw is not None else None

    return {
        "today_win": today_win,
        "today_loss": today_loss,
        "today_hold": today_hold,
        "all_time_decisions": total_dec,
        "discipline_hold_rate": round(float(hold_rate), 4) if hold_rate is not None else None,
        "confluence_avg": conf_avg,
    }
