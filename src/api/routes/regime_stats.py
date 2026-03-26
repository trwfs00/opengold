from fastapi import APIRouter
from src.db import execute

router = APIRouter()

REGIME_COLORS = {
    "TRENDING": "trending",
    "RANGING": "ranging",
    "BREAKOUT": "breakout",
    "TRANSITIONAL": "transitional",
}


@router.get("/regime-stats")
def get_regime_stats():
    try:
        rows = execute(
            """
            SELECT regime, COUNT(*) AS cnt
            FROM decisions
            WHERE regime IS NOT NULL
            GROUP BY regime
            ORDER BY cnt DESC
            """,
            fetch=True,
        )
    except Exception:
        return {"error": "Database unavailable", "stats": {}, "total": 0}

    total = sum(r[1] for r in rows) if rows else 0
    stats = {}
    for regime, cnt in rows:
        key = regime.upper() if regime else "UNKNOWN"
        stats[key] = {
            "count": cnt,
            "pct": round(cnt / total * 100, 1) if total else 0,
        }
    return {"stats": stats, "total": total}
