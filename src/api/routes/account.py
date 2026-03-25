from fastapi import APIRouter
from src.mt5_bridge.connection import is_connected, get_account_info
from src.mt5_bridge.data import get_positions

router = APIRouter()


@router.get("/account")
def get_account():
    info = get_account_info()
    if not info and not is_connected():
        return {"error": "MT5 disconnected"}
    positions = get_positions()
    return {
        "balance": info.get("balance"),
        "equity": info.get("equity"),
        "currency": info.get("currency"),
        "positions": positions,
    }
