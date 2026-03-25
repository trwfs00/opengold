from fastapi import APIRouter
router = APIRouter()

@router.get("/account")
def get_account():
    return {"balance": None, "equity": None, "currency": None, "positions": []}
