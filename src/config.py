import os
from dotenv import load_dotenv

load_dotenv()

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

# Risk
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.01"))
MAX_CONCURRENT_TRADES = int(os.getenv("MAX_CONCURRENT_TRADES", "3"))
DAILY_DRAWDOWN_LIMIT = float(os.getenv("DAILY_DRAWDOWN_LIMIT", "0.05"))
MIN_AI_CONFIDENCE = float(os.getenv("MIN_AI_CONFIDENCE", "0.65"))
MIN_SL_USD = float(os.getenv("MIN_SL_USD", "3.00"))
MAX_SL_USD = float(os.getenv("MAX_SL_USD", "50.00"))

# Regime
ADX_TREND_THRESHOLD = float(os.getenv("ADX_TREND_THRESHOLD", "25"))
ATR_BREAKOUT_MULTIPLIER = float(os.getenv("ATR_BREAKOUT_MULTIPLIER", "1.5"))
ATR_LOOKBACK = int(os.getenv("ATR_LOOKBACK", "14"))
BB_WIDTH_THRESHOLD = float(os.getenv("BB_WIDTH_THRESHOLD", "0.001"))
BB_LOOKBACK = int(os.getenv("BB_LOOKBACK", "20"))

# Trigger
TRIGGER_MIN_SCORE = float(os.getenv("TRIGGER_MIN_SCORE", "5.0"))
TRIGGER_MIN_SCORE_DIFF = float(os.getenv("TRIGGER_MIN_SCORE_DIFF", "2.0"))

# System
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "5"))
JOURNAL_TRADE_COUNT = int(os.getenv("JOURNAL_TRADE_COUNT", "10"))
DB_BUFFER_MAX_RECORDS = int(os.getenv("DB_BUFFER_MAX_RECORDS", "1000"))
DB_RETRY_INTERVAL_SECONDS = int(os.getenv("DB_RETRY_INTERVAL_SECONDS", "30"))
DB_MAX_RETRY_DURATION_SECONDS = int(os.getenv("DB_MAX_RETRY_DURATION_SECONDS", "3600"))
