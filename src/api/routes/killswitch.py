from fastapi import APIRouter
from pydantic import BaseModel
router = APIRouter()

class KillSwitchRequest(BaseModel):
    active: bool

@router.post("/killswitch")
def set_killswitch(body: KillSwitchRequest):
    return {"active": body.active}
