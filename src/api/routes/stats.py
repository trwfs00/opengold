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

    empty = {
        "win_rate": None, "total_pnl": 0.0, "avg_win": None, "avg_loss": None,
        "pnl_curve": [], "win_count": 0, "loss_count": 0, "total_trades": 0,
        "current_streak": 0, "avg_rr": None, "last_15": [],
    }
    if not rows:
        return empty

    wins = [r[1] for r in rows if r[2] == "WIN"]
    losses = [r[1] for r in rows if r[2] == "LOSS"]
    total = len(rows)
    win_rate = len(wins) / total if total else None
    total_pnl = sum(r[1] for r in rows)
    avg_win = sum(wins) / len(wins) if wins else None
    avg_loss = sum(losses) / len(losses) if losses else None
    avg_rr = (avg_win / abs(avg_loss)) if avg_win and avg_loss and avg_loss != 0 else None

    # Current consecutive streak (WIN/LOSS only, ignore BREAKEVEN)
    wl_rows = [r[2] for r in rows if r[2] in ("WIN", "LOSS")]
    current_streak = 0
    if wl_rows:
        last_result = wl_rows[-1]
        for result in reversed(wl_rows):
            if result == last_result:
                current_streak += 1
            else:
                break
        if last_result == "LOSS":
            current_streak = -current_streak

    last_15 = [r[2] for r in rows[-15:]]

    cumulative = 0.0
    pnl_curve = []
    for close_time, pnl, _ in rows:
        cumulative += pnl
        t = int(close_time.timestamp())
        # lightweight-charts requires strictly ascending times; merge duplicates
        if pnl_curve and pnl_curve[-1]["time"] >= t:
            pnl_curve[-1]["value"] = round(cumulative, 2)
        else:
            pnl_curve.append({"time": t, "value": round(cumulative, 2)})

    # Max Drawdown: largest peak-to-trough drop in cumulative P&L
    peak = 0.0
    max_dd = 0.0
    for pt in pnl_curve:
        v = pt["value"]
        if v > peak:
            peak = v
        dd = peak - v
        if dd > max_dd:
            max_dd = dd

    # Profit Factor = gross_profit / |gross_loss|  (None if no losses)
    gross_profit = sum(w for w in wins if w > 0)
    gross_loss = abs(sum(l for l in losses if l < 0))
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else None

    # Expectancy = expected P&L per trade
    expectancy = round(
        (win_rate * avg_win) + ((1 - win_rate) * avg_loss), 2
    ) if win_rate is not None and avg_win is not None and avg_loss is not None else None

    return {
        "win_rate": round(win_rate, 4) if win_rate is not None else None,
        "total_pnl": round(total_pnl, 2),
        "avg_win": round(avg_win, 2) if avg_win is not None else None,
        "avg_loss": round(avg_loss, 2) if avg_loss is not None else None,
        "pnl_curve": pnl_curve,
        "win_count": len(wins),
        "loss_count": len(losses),
        "total_trades": total,
        "current_streak": current_streak,
        "avg_rr": round(avg_rr, 2) if avg_rr is not None else None,
        "last_15": last_15,
        "max_drawdown": round(max_dd, 2),
        "profit_factor": profit_factor,
        "expectancy": expectancy,
    }
