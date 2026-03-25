from fastapi import APIRouter
from src.mt5_bridge.data import fetch_candles
from src.mt5_bridge.connection import is_connected

router = APIRouter()


@router.get("/candles")
def get_candles(limit: int = 200):
    df = fetch_candles(limit)
    if df.empty and not is_connected():
        return {"error": "MT5 disconnected", "data": None}
    records = []
    for _, row in df.iterrows():
        records.append({
            "time": int(row["time"].timestamp()),
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume": row["volume"],
        })
    return {"data": records}
