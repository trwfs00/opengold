from fastapi import APIRouter
router = APIRouter()

@router.get("/stats")
def get_stats():
    return {"win_rate": None, "total_pnl": 0.0, "avg_win": None, "avg_loss": None, "pnl_curve": []}
