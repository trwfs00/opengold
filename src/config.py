import os
from dotenv import load_dotenv

load_dotenv(os.getenv("ENV_FILE", ".env"), override=True)

# MT5
MT5_LOGIN = int(os.environ["MT5_LOGIN"])
MT5_PASSWORD = os.environ["MT5_PASSWORD"]
MT5_SERVER = os.environ["MT5_SERVER"]

# Database
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "opengold")
DB_USER = os.getenv("DB_USER", "opengold")
DB_PASSWORD = os.environ["DB_PASSWORD"]

# AI
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_PRIMARY_MODEL = os.getenv("CLAUDE_PRIMARY_MODEL", "claude-haiku-4-5")
CLAUDE_FALLBACK_MODEL = os.getenv("CLAUDE_FALLBACK_MODEL", "claude-sonnet-4-5")
if not ANTHROPIC_API_KEY:
    import logging as _logging
    _logging.getLogger(__name__).warning("ANTHROPIC_API_KEY not set — AI calls will fail at runtime")

# Risk
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.01"))
MAX_CONCURRENT_TRADES = int(os.getenv("MAX_CONCURRENT_TRADES", "10"))
DAILY_DRAWDOWN_LIMIT = float(os.getenv("DAILY_DRAWDOWN_LIMIT", "0.05"))
MIN_AI_CONFIDENCE = float(os.getenv("MIN_AI_CONFIDENCE", "0.65"))
MIN_SL_USD = float(os.getenv("MIN_SL_USD", "3.00"))
MAX_SL_USD = float(os.getenv("MAX_SL_USD", "25.00"))
MIN_TP_USD = float(os.getenv("MIN_TP_USD", "5.00"))
MIN_RR_RATIO = float(os.getenv("MIN_RR_RATIO", "1.5"))

# Multi-symbol
BOT_ID = os.getenv("BOT_ID", "gold")
SYMBOL = os.getenv("SYMBOL", "XAUUSD")
TIMEFRAME = os.getenv("TIMEFRAME", "M1")
CONTRACT_SIZE = float(os.getenv("CONTRACT_SIZE", "100"))      # Gold = 100 oz/lot
PIP_VALUE_PER_LOT = float(os.getenv("PIP_VALUE_PER_LOT", "10"))
SL_PIPS_MIN = float(os.getenv("SL_PIPS_MIN", "3"))
SL_PIPS_MAX = float(os.getenv("SL_PIPS_MAX", "50"))
TP_PIPS_MIN = float(os.getenv("TP_PIPS_MIN", "4"))   # used by prompt.py for guidance text only
TP_PIPS_MAX = float(os.getenv("TP_PIPS_MAX", "10"))  # used by prompt.py for guidance text only
MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", "999"))

# Regime
ADX_TREND_THRESHOLD = float(os.getenv("ADX_TREND_THRESHOLD", "25"))
ATR_BREAKOUT_MULTIPLIER = float(os.getenv("ATR_BREAKOUT_MULTIPLIER", "1.5"))
ATR_LOOKBACK = int(os.getenv("ATR_LOOKBACK", "14"))
BB_WIDTH_THRESHOLD = float(os.getenv("BB_WIDTH_THRESHOLD", "0.001"))
BB_LOOKBACK = int(os.getenv("BB_LOOKBACK", "20"))

# Trigger (kept for reference / dashboard tooltip)
TRIGGER_MIN_SCORE = float(os.getenv("TRIGGER_MIN_SCORE", "4.0"))
TRIGGER_MIN_SCORE_DIFF = float(os.getenv("TRIGGER_MIN_SCORE_DIFF", "1.0"))
# AI decision interval (minutes between Claude calls)
AI_INTERVAL_MINUTES = int(os.getenv("AI_INTERVAL_MINUTES", "5"))
# Active trading sessions (UTC hours). Format: "start1-end1,start2-end2"
# Default: London open + NY overlap (most liquid for gold)
# Set to "0-24" to trade all hours
TRADE_SESSIONS_UTC = os.getenv("TRADE_SESSIONS_UTC", "0-24")

# System
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "5"))
JOURNAL_TRADE_COUNT = int(os.getenv("JOURNAL_TRADE_COUNT", "10"))
DB_BUFFER_MAX_RECORDS = int(os.getenv("DB_BUFFER_MAX_RECORDS", "1000"))
DB_RETRY_INTERVAL_SECONDS = int(os.getenv("DB_RETRY_INTERVAL_SECONDS", "30"))
DB_MAX_RETRY_DURATION_SECONDS = int(os.getenv("DB_MAX_RETRY_DURATION_SECONDS", "3600"))

# Production mode
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
MT5_RECONNECT_RETRIES = int(os.getenv("MT5_RECONNECT_RETRIES", "3"))
MT5_RECONNECT_DELAY_BASE = int(os.getenv("MT5_RECONNECT_DELAY_BASE", "2"))

# Position Manager (trailing stop + AI re-evaluation)
TRAIL_ENABLED = os.getenv("TRAIL_ENABLED", "true").lower() == "true"
# Move SL to breakeven when unrealised profit reaches this fraction of TP distance
TRAIL_BE_RATIO = float(os.getenv("TRAIL_BE_RATIO", "0.5"))
# After breakeven: trail SL at (price − ATR × multiplier) for BUY, inverse for SELL
TRAIL_ATR_MULTIPLIER = float(os.getenv("TRAIL_ATR_MULTIPLIER", "1.5"))
# USD profit floor: when unrealised PnL >= this value, force breakeven regardless of TP
# (0 = disabled; set to a value like 50-100 so no-TP positions still get trailed)
TRAIL_MIN_PROFIT_USD = float(os.getenv("TRAIL_MIN_PROFIT_USD", "0"))
# Re-evaluate open positions with AI every N minutes (0 = disabled)
REEVAL_INTERVAL_MINUTES = int(os.getenv("REEVAL_INTERVAL_MINUTES", "5"))
# Minimum counter-signal strength to trigger AI re-evaluation
REEVAL_MIN_COUNTER_SCORE = float(os.getenv("REEVAL_MIN_COUNTER_SCORE", "5.0"))
# Partial close: fraction of the position to close when AI says PARTIAL_CLOSE (0 = disabled)
PARTIAL_CLOSE_RATIO = float(os.getenv("PARTIAL_CLOSE_RATIO", "0.5"))

# Dashboard API  (API_PORT overrides DASHBOARD_API_PORT for multi-bot support)
DASHBOARD_API_HOST = os.getenv("DASHBOARD_API_HOST", "127.0.0.1")
DASHBOARD_API_PORT = int(os.getenv("API_PORT", os.getenv("DASHBOARD_API_PORT", "8000")))
