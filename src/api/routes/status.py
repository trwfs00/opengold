from datetime import datetime, timezone, timedelta
from fastapi import APIRouter
from src.db import execute
from src.logger.writer import get_kill_switch_state
from src import config

router = APIRouter()
BOT_ALIVE_THRESHOLD_SECONDS = 60


@router.get("/status")
def get_status():
    try:
        rows = execute(
            "SELECT time FROM decisions ORDER BY time DESC LIMIT 1",
            fetch=True,
        )
    except Exception:
        return {"error": "Database unavailable"}

    bot_alive = False
    if rows:
        last_decision = rows[0][0]
        if last_decision.tzinfo is None:
            last_decision = last_decision.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - last_decision).total_seconds()
        bot_alive = age < BOT_ALIVE_THRESHOLD_SECONDS

    kill_switch = get_kill_switch_state()
    return {
        "bot_alive": bot_alive,
        "dry_run": config.DRY_RUN,
        "kill_switch_active": kill_switch,
    }
