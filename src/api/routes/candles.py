from fastapi import APIRouter
router = APIRouter()

@router.get("/candles")
def get_candles(limit: int = 200):
    return {"data": []}
