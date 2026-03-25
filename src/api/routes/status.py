from fastapi import APIRouter
router = APIRouter()

@router.get("/status")
def get_status():
    return {"bot_alive": False, "dry_run": False, "kill_switch_active": False}
