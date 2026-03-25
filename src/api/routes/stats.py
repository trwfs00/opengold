from fastapi import APIRouter
from src.db import execute

router = APIRouter()


@router.get("/stats")
def get_stats():
    try:
        rows = execute(
            "SELECT close_time, pnl, result FROM trades ORDER BY close_time ASC",
            fetch=True,
        )
    except Exception:
        return {"error": "Database unavailable"}

    if not rows:
        return {
            "win_rate": None, "total_pnl": 0.0,
            "avg_win": None, "avg_loss": None, "pnl_curve": [],
        }

    wins = [r[1] for r in rows if r[2] == "WIN"]
    losses = [r[1] for r in rows if r[2] == "LOSS"]
    total = len(rows)
    win_rate = len(wins) / total if total else None
    total_pnl = sum(r[1] for r in rows)
    avg_win = sum(wins) / len(wins) if wins else None
    avg_loss = sum(losses) / len(losses) if losses else None

    cumulative = 0.0
    pnl_curve = []
    for close_time, pnl, _ in rows:
        cumulative += pnl
        pnl_curve.append({"time": int(close_time.timestamp()), "value": round(cumulative, 2)})

    return {
        "win_rate": round(win_rate, 4) if win_rate is not None else None,
        "total_pnl": round(total_pnl, 2),
        "avg_win": round(avg_win, 2) if avg_win is not None else None,
        "avg_loss": round(avg_loss, 2) if avg_loss is not None else None,
        "pnl_curve": pnl_curve,
    }
