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
    last_ai_time = None
    if rows:
        last_decision = rows[0][0]
        if last_decision.tzinfo is None:
            last_decision = last_decision.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - last_decision).total_seconds()
        bot_alive = age < BOT_ALIVE_THRESHOLD_SECONDS
        last_ai_time = last_decision.isoformat()

    kill_switch = get_kill_switch_state()
    # Format model name for display:
    # "claude-haiku-4-5"        → "claude-haiku-4.5"
    # "claude-3-5-haiku-20241022" → "claude-3.5-haiku"
    def _short(name: str) -> str:
        parts = name.split("-")
        # strip trailing date stamps (≥6 consecutive digits, e.g. 20241022)
        parts = [p for p in parts if not (p.isdigit() and len(p) >= 6)]
        # merge adjacent single/double-digit parts with a dot (version numbers)
        result: list[str] = []
        i = 0
        while i < len(parts):
            if parts[i].isdigit() and i + 1 < len(parts) and parts[i + 1].isdigit():
                result.append(f"{parts[i]}.{parts[i + 1]}")
                i += 2
            else:
                result.append(parts[i])
                i += 1
        return "-".join(result)

    return {
        "bot_alive": bot_alive,
        "dry_run": config.DRY_RUN,
        "kill_switch_active": kill_switch,
        "ai_model": _short(config.CLAUDE_PRIMARY_MODEL),
        "last_ai_time": last_ai_time,
        "ai_interval_minutes": config.AI_INTERVAL_MINUTES,
    }
