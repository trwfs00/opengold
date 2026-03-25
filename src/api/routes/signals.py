import json
from fastapi import APIRouter
from src.db import execute
from src.mt5_bridge.connection import is_connected

router = APIRouter()


@router.get("/signals")
def get_signals():
    connected = is_connected()
    try:
        rows = execute(
            "SELECT regime, buy_score, sell_score, signals FROM decisions ORDER BY time DESC LIMIT 1",
            fetch=True,
        )
    except Exception:
        return {"error": "Database unavailable"}
    if not rows:
        return {
            "signals": None, "regime": None, "buy_score": None, "sell_score": None,
            "connected": connected, "message": "No data yet",
        }
    regime, buy_score, sell_score, signals_raw = rows[0]
    signals = json.loads(signals_raw) if signals_raw else None
    return {
        "regime": regime, "buy_score": buy_score, "sell_score": sell_score,
        "signals": signals, "connected": connected,
    }
