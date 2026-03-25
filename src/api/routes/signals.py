from fastapi import APIRouter
router = APIRouter()

@router.get("/signals")
def get_signals():
    return {"signals": None, "regime": None, "buy_score": None, "sell_score": None, "connected": False, "message": "No data yet"}
