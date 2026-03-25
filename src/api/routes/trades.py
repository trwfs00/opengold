from fastapi import APIRouter
router = APIRouter()

@router.get("/trades")
def get_trades(limit: int = 50):
    return {"data": []}
