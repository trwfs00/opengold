from fastapi import APIRouter
router = APIRouter()

@router.get("/decisions")
def get_decisions(limit: int = 50):
    return {"data": []}
