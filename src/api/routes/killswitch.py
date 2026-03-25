from fastapi import APIRouter
from pydantic import BaseModel
from src.logger.writer import set_kill_switch

router = APIRouter()


class KillSwitchRequest(BaseModel):
    active: bool


@router.post("/killswitch")
def toggle_kill_switch(body: KillSwitchRequest):
    set_kill_switch(body.active)
    return {"active": body.active}
