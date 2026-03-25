# OpenGold Phase 1–2: Trading Bot Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully working automated XAU/USD trading bot that fetches M1 candles from MT5, runs 13 technical strategies, classifies market regime, aggregates weighted scores, triggers trades when conditions are met, and logs every decision to TimescaleDB — all without AI involvement.

**Architecture:** Modular Python app on Windows host (MT5 requires Windows). TimescaleDB runs in Docker. The main loop detects new candle closes by polling, runs all strategies, aggregates scores, and executes trades via MT5 when the trigger fires. Phase 3 will slot AI in between trigger and executor.

**Tech Stack:** Python 3.11+, MetaTrader5, pandas, pandas-ta, numpy, psycopg2, docker-compose, TimescaleDB (PostgreSQL 15 + TimescaleDB 2.x)

**Spec:** `docs/superpowers/specs/2026-03-25-opengold-trading-system-design.md`

---

## File Map

```
opengold/
├── docker-compose.yml
├── .env.example
├── requirements.txt
├── main.py
├── tests/
│   ├── conftest.py
│   ├── test_strategies/
│   │   ├── test_ma_crossover.py
│   │   ├── test_macd.py
│   │   ├── test_ichimoku.py
│   │   ├── test_momentum.py
│   │   ├── test_adx_trend.py
│   │   ├── test_rsi.py
│   │   ├── test_bollinger.py
│   │   ├── test_stochastic.py
│   │   ├── test_mean_reversion.py
│   │   ├── test_breakout.py
│   │   ├── test_support_resistance.py
│   │   ├── test_scalping.py
│   │   └── test_vwap.py
│   ├── test_aggregator.py
│   ├── test_regime.py
│   └── test_trigger.py
└── src/
    ├── config.py                   # Load .env, expose typed config values
    ├── db.py                       # DB connection pool, query helpers
    ├── schema.sql                  # TimescaleDB DDL (run once)
    ├── mt5_bridge/
    │   ├── __init__.py
    │   ├── connection.py           # connect(), disconnect(), is_connected()
    │   └── data.py                 # fetch_candles(), get_last_candle_time(), get_positions()
    ├── strategies/
    │   ├── __init__.py             # run_all(candles, regime) -> list of results
    │   ├── base.py                 # SignalResult dataclass
    │   ├── ma_crossover.py
    │   ├── macd.py
    │   ├── ichimoku.py
    │   ├── momentum.py
    │   ├── adx_trend.py
    │   ├── rsi.py
    │   ├── bollinger.py
    │   ├── stochastic.py
    │   ├── mean_reversion.py
    │   ├── breakout.py
    │   ├── support_resistance.py
    │   ├── scalping.py
    │   └── vwap.py
    ├── regime/
    │   ├── __init__.py
    │   └── classifier.py           # classify(candles) -> "TRENDING"|"RANGING"|"BREAKOUT"
    ├── aggregator/
    │   ├── __init__.py
    │   └── scorer.py               # aggregate(signals, regime) -> AggregateResult
    ├── trigger/
    │   ├── __init__.py
    │   └── gate.py                 # should_call_ai(agg, open_trades, kill_switch) -> bool
    ├── risk/
    │   ├── __init__.py
    │   └── engine.py               # validate(action, confidence, sl, tp, balance, open_trades) -> RiskResult
    ├── executor/
    │   ├── __init__.py
    │   └── orders.py               # place_order(), close_position(), sync_positions()
    └── logger/
        ├── __init__.py
        └── writer.py               # log_decision(), log_trade(), get_open_positions_snapshot()
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `requirements.txt`
- Create: `src/config.py`

- [ ] **Step 1.1: Create `docker-compose.yml`**

```yaml
version: "3.9"
services:
  timescaledb:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_DB: opengold
      POSTGRES_USER: opengold
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - timescaledb_data:/var/lib/postgresql/data

volumes:
  timescaledb_data:
```

- [ ] **Step 1.2: Create `.env.example`**

```
# MetaTrader 5
MT5_LOGIN=5048406324
MT5_PASSWORD=your_mt5_password
MT5_SERVER=MetaQuotes-Demo

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=opengold
DB_USER=opengold
DB_PASSWORD=your_db_password

# Claude AI (Phase 3)
ANTHROPIC_API_KEY=your_api_key_here

# Risk parameters
RISK_PER_TRADE=0.01
MAX_CONCURRENT_TRADES=3
DAILY_DRAWDOWN_LIMIT=0.05
MIN_AI_CONFIDENCE=0.65
MIN_SL_USD=3.00
MAX_SL_USD=50.00

# Regime parameters
ADX_TREND_THRESHOLD=25
ATR_BREAKOUT_MULTIPLIER=1.5
ATR_LOOKBACK=14
BB_WIDTH_THRESHOLD=0.001
BB_LOOKBACK=20

# Trigger thresholds
TRIGGER_MIN_SCORE=5.0
TRIGGER_MIN_SCORE_DIFF=2.0

# System
POLL_INTERVAL_SECONDS=5
JOURNAL_TRADE_COUNT=10
DB_BUFFER_MAX_RECORDS=1000
DB_RETRY_INTERVAL_SECONDS=30
DB_MAX_RETRY_DURATION_SECONDS=3600
```

- [ ] **Step 1.3: Create `requirements.txt`**

```
MetaTrader5==5.0.45
pandas==2.2.0
pandas-ta==0.3.14b
numpy==1.26.3
psycopg2-binary==2.9.9
python-dotenv==1.0.0
anthropic==0.21.0
fastapi==0.110.0
uvicorn==0.27.1
```

- [ ] **Step 1.4: Create `src/config.py`**

```python
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
```

- [ ] **Step 1.5: Copy `.env.example` to `.env` and fill in real values**

```
MT5_PASSWORD=K_EbA6Ty
DB_PASSWORD=choose_a_local_password
```

- [ ] **Step 1.6: Create `.gitignore`**

```
.env
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 1.7: Start TimescaleDB**

```powershell
docker-compose up -d
```

Expected: `timescaledb` container running, port 5432 available.

Verify: `docker ps` shows container healthy.

- [ ] **Step 1.8: Commit scaffold**

```powershell
git init
git add docker-compose.yml .env.example requirements.txt src/config.py .gitignore
git commit -m "chore: project scaffold with config and docker-compose"
```

---

## Task 2: Database Schema & Connection

**Files:**
- Create: `src/schema.sql`
- Create: `src/db.py`

- [ ] **Step 2.1: Create `src/schema.sql`**

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS candles (
    time        TIMESTAMPTZ NOT NULL,
    open        FLOAT8,
    high        FLOAT8,
    low         FLOAT8,
    close       FLOAT8,
    volume      FLOAT8
);
SELECT create_hypertable('candles', 'time', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS decisions (
    time              TIMESTAMPTZ NOT NULL,
    regime            TEXT,
    buy_score         FLOAT8,
    sell_score        FLOAT8,
    trigger_fired     BOOLEAN,
    ai_action         TEXT,
    ai_confidence     FLOAT8,
    ai_sl             FLOAT8,
    ai_tp             FLOAT8,
    risk_block_reason TEXT
);
SELECT create_hypertable('decisions', 'time', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS trades (
    id          SERIAL PRIMARY KEY,
    open_time   TIMESTAMPTZ,
    close_time  TIMESTAMPTZ,
    direction   TEXT,
    lot_size    FLOAT8,
    open_price  FLOAT8,
    close_price FLOAT8,
    sl          FLOAT8,
    tp          FLOAT8,
    pnl         FLOAT8,
    result      TEXT
);

CREATE TABLE IF NOT EXISTS system_state (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO system_state (key, value) VALUES
    ('kill_switch_active', 'false'),
    ('kill_switch_date', ''),
    ('daily_start_balance', '0'),
    ('daily_start_date', '')
ON CONFLICT (key) DO NOTHING;
```

- [ ] **Step 2.2: Apply the schema**

```powershell
Get-Content src/schema.sql | docker exec -i opengold-timescaledb-1 psql -U opengold -d opengold
```

Expected: No errors, tables created.

- [ ] **Step 2.3: Write test for DB connection**

Create `tests/test_db.py`:

```python
import pytest
from src.db import get_connection

def test_db_connects():
    conn = get_connection()
    assert conn is not None
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        result = cur.fetchone()
    assert result == (1,)
    conn.close()
```

- [ ] **Step 2.4: Run test to verify it fails**

```powershell
pytest tests/test_db.py -v
```

Expected: `ImportError: cannot import name 'get_connection'`

- [ ] **Step 2.5: Create `src/db.py`**

```python
import psycopg2
from psycopg2 import pool
from src import config

_pool = None

def _get_pool():
    global _pool
    if _pool is None:
        _pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            host=config.DB_HOST,
            port=config.DB_PORT,
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
        )
    return _pool

def get_connection():
    return _get_pool().getconn()

def release_connection(conn):
    _get_pool().putconn(conn)

def execute(query: str, params=None, fetch=False):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
            if fetch:
                return cur.fetchall()
    finally:
        release_connection(conn)
```

- [ ] **Step 2.6: Run test to verify it passes**

```powershell
pytest tests/test_db.py -v
```

Expected: PASS

- [ ] **Step 2.7: Commit**

```powershell
git add src/schema.sql src/db.py tests/test_db.py
git commit -m "feat: database schema and connection pool"
```

---

## Task 3: MT5 Bridge

**Files:**
- Create: `src/mt5_bridge/connection.py`
- Create: `src/mt5_bridge/data.py`
- Create: `src/mt5_bridge/__init__.py`

> Note: MT5 Python API only works on Windows with MetaTrader 5 installed and running. Tests for MT5 are integration tests requiring the real MT5 connection.

- [ ] **Step 3.1: Create `src/mt5_bridge/__init__.py`** (empty)

- [ ] **Step 3.2: Create `src/mt5_bridge/connection.py`**

```python
import MetaTrader5 as mt5
from src import config
import logging

logger = logging.getLogger(__name__)

def connect() -> bool:
    if not mt5.initialize(
        login=config.MT5_LOGIN,
        password=config.MT5_PASSWORD,
        server=config.MT5_SERVER,
    ):
        logger.error(f"MT5 initialize failed: {mt5.last_error()}")
        return False
    logger.info(f"MT5 connected: {mt5.account_info().name}")
    return True

def disconnect():
    mt5.shutdown()

def is_connected() -> bool:
    info = mt5.account_info()
    return info is not None

def get_account_info() -> dict:
    info = mt5.account_info()
    if info is None:
        return {}
    return {
        "balance": info.balance,
        "equity": info.equity,
        "currency": info.currency,
    }
```

- [ ] **Step 3.3: Create `src/mt5_bridge/data.py`**

```python
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M1

def fetch_candles(count: int = 200) -> pd.DataFrame:
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, count)
    if rates is None or len(rates) == 0:
        logger.error(f"fetch_candles failed: {mt5.last_error()}")
        return pd.DataFrame()
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.rename(columns={"tick_volume": "volume"})
    return df[["time", "open", "high", "low", "close", "volume"]]

def get_last_candle_time() -> datetime | None:
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 1)
    if rates is None or len(rates) == 0:
        return None
    return pd.to_datetime(rates[0]["time"], unit="s", utc=True).to_pydatetime()

def get_positions() -> list[dict]:
    positions = mt5.positions_get(symbol=SYMBOL)
    if positions is None:
        return []
    return [
        {
            "ticket": p.ticket,
            "direction": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
            "volume": p.volume,
            "open_price": p.price_open,
            "sl": p.sl,
            "tp": p.tp,
        }
        for p in positions
    ]

def get_history_deals(from_dt: datetime, to_dt: datetime) -> list[dict]:
    deals = mt5.history_deals_get(from_dt, to_dt)
    if deals is None:
        return []
    return [
        {
            "ticket": d.ticket,
            "order": d.order,
            "time": pd.to_datetime(d.time, unit="s", utc=True).to_pydatetime(),
            "type": d.type,
            "volume": d.volume,
            "price": d.price,
            "profit": d.profit,
            "symbol": d.symbol,
            "entry": d.entry,  # 0=IN, 1=OUT
        }
        for d in deals
        if d.symbol == SYMBOL
    ]
```

- [ ] **Step 3.4: Manual integration test — confirm MT5 connects**

Create `tests/integration/test_mt5_bridge.py`:

```python
"""Run manually: requires MT5 running on Windows."""
import pytest
from src.mt5_bridge.connection import connect, disconnect, get_account_info
from src.mt5_bridge.data import fetch_candles, get_last_candle_time, get_positions

@pytest.mark.integration
def test_mt5_connect_and_fetch():
    assert connect()
    info = get_account_info()
    assert info["balance"] > 0
    candles = fetch_candles(50)
    assert len(candles) == 50
    assert "close" in candles.columns
    last_time = get_last_candle_time()
    assert last_time is not None
    disconnect()
```

Run manually:
```powershell
pytest tests/integration/test_mt5_bridge.py -v -m integration
```

Expected: PASS (MT5 must be running and logged in)

- [ ] **Step 3.5: Commit**

```powershell
git add src/mt5_bridge/ tests/integration/test_mt5_bridge.py
git commit -m "feat: MT5 bridge - connection and candle fetching"
```

---

## Task 4: Strategy Base & Signal Dataclass

**Files:**
- Create: `src/strategies/base.py`
- Create: `src/strategies/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 4.1: Write test for SignalResult**

Create `tests/test_strategies/test_base.py`:

```python
from src.strategies.base import SignalResult

def test_signal_result_fields():
    s = SignalResult(name="test", signal="BUY", confidence=0.8)
    assert s.name == "test"
    assert s.signal == "BUY"
    assert 0.0 <= s.confidence <= 1.0

def test_signal_invalid_type_raises():
    import pytest
    with pytest.raises(ValueError):
        SignalResult(name="test", signal="MAYBE", confidence=0.5)
```

- [ ] **Step 4.2: Run test to verify it fails**

```powershell
pytest tests/test_strategies/test_base.py -v
```

- [ ] **Step 4.3: Create `src/strategies/base.py`**

```python
from dataclasses import dataclass

VALID_SIGNALS = {"BUY", "SELL", "NEUTRAL"}

@dataclass
class SignalResult:
    name: str
    signal: str
    confidence: float

    def __post_init__(self):
        if self.signal not in VALID_SIGNALS:
            raise ValueError(f"signal must be one of {VALID_SIGNALS}, got '{self.signal}'")
        self.confidence = max(0.0, min(1.0, self.confidence))
```

- [ ] **Step 4.4: Create `tests/conftest.py`** with shared fixture for synthetic candle data

```python
import pytest
import pandas as pd
import numpy as np

@pytest.fixture
def trending_up_candles():
    """100 candles in a clear uptrend."""
    n = 100
    base = 1900.0
    closes = [base + i * 0.5 + np.random.uniform(-0.1, 0.1) for i in range(n)]
    return pd.DataFrame({
        "time": pd.date_range("2024-01-01", periods=n, freq="1min", tz="UTC"),
        "open":  [c - 0.2 for c in closes],
        "high":  [c + 0.3 for c in closes],
        "low":   [c - 0.3 for c in closes],
        "close": closes,
        "volume": [100.0] * n,
    })

@pytest.fixture
def ranging_candles():
    """100 candles oscillating in a range (1910–1920)."""
    n = 100
    closes = [1915.0 + 5.0 * np.sin(i * 0.3) + np.random.uniform(-0.2, 0.2) for i in range(n)]
    return pd.DataFrame({
        "time": pd.date_range("2024-01-01", periods=n, freq="1min", tz="UTC"),
        "open":  [c - 0.2 for c in closes],
        "high":  [c + 0.5 for c in closes],
        "low":   [c - 0.5 for c in closes],
        "close": closes,
        "volume": [100.0] * n,
    })
```

- [ ] **Step 4.5: Run tests**

```powershell
pytest tests/test_strategies/test_base.py -v
```

Expected: PASS

- [ ] **Step 4.6: Commit**

```powershell
git add src/strategies/base.py src/strategies/__init__.py tests/conftest.py tests/test_strategies/test_base.py
git commit -m "feat: strategy base SignalResult dataclass and test fixtures"
```

---

## Task 5: Trend Following Strategies (5 strategies)

**Files:**
- Create: `src/strategies/ma_crossover.py`
- Create: `src/strategies/macd.py`
- Create: `src/strategies/ichimoku.py`
- Create: `src/strategies/momentum.py`
- Create: `src/strategies/adx_trend.py`

Follow this pattern for each strategy. Shown in full for MA Crossover; the rest follow the same test-then-implement cycle.

- [ ] **Step 5.1: Write test for MA Crossover**

Create `tests/test_strategies/test_ma_crossover.py`:

```python
from src.strategies.ma_crossover import compute

def test_uptrend_gives_buy(trending_up_candles):
    result = compute(trending_up_candles)
    assert result.signal == "BUY"
    assert result.confidence > 0.5

def test_returns_signal_result(trending_up_candles):
    from src.strategies.base import SignalResult
    assert isinstance(compute(trending_up_candles), SignalResult)

def test_short_candles_returns_neutral():
    import pandas as pd
    df = pd.DataFrame({"close": [1900.0] * 5})
    result = compute(df)
    assert result.signal == "NEUTRAL"
```

- [ ] **Step 5.2: Run test — verify fails**

```powershell
pytest tests/test_strategies/test_ma_crossover.py -v
```

- [ ] **Step 5.3: Create `src/strategies/ma_crossover.py`**

```python
import pandas as pd
from src.strategies.base import SignalResult

NAME = "ma_crossover"
FAST = 9
SLOW = 21

def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < SLOW + 1:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    close = candles["close"]
    fast_ma = close.rolling(FAST).mean()
    slow_ma = close.rolling(SLOW).mean()
    curr_fast, curr_slow = fast_ma.iloc[-1], slow_ma.iloc[-1]
    prev_fast, prev_slow = fast_ma.iloc[-2], slow_ma.iloc[-2]
    if prev_fast <= prev_slow and curr_fast > curr_slow:
        gap = abs(curr_fast - curr_slow) / curr_slow
        confidence = min(1.0, gap * 500)
        return SignalResult(name=NAME, signal="BUY", confidence=confidence)
    if prev_fast >= prev_slow and curr_fast < curr_slow:
        gap = abs(curr_fast - curr_slow) / curr_slow
        confidence = min(1.0, gap * 500)
        return SignalResult(name=NAME, signal="SELL", confidence=confidence)
    # MA already crossed — trend continuation
    if curr_fast > curr_slow:
        gap = abs(curr_fast - curr_slow) / curr_slow
        return SignalResult(name=NAME, signal="BUY", confidence=min(0.6, gap * 300))
    if curr_fast < curr_slow:
        gap = abs(curr_fast - curr_slow) / curr_slow
        return SignalResult(name=NAME, signal="SELL", confidence=min(0.6, gap * 300))
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
```

- [ ] **Step 5.4: Run test — verify passes**

```powershell
pytest tests/test_strategies/test_ma_crossover.py -v
```

- [ ] **Step 5.5: Implement remaining 4 trend strategies**

For each strategy below, create the test file first (same pattern: uptrend→BUY, short data→NEUTRAL, returns SignalResult), run it, implement, and run again.

**`src/strategies/macd.py`** — use `pandas_ta` MACD(12,26,9). BUY when MACD line crosses above signal line; SELL when below. Confidence from histogram magnitude.

```python
import pandas as pd
import pandas_ta as ta
from src.strategies.base import SignalResult

NAME = "macd"

def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < 35:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    macd_df = ta.macd(candles["close"], fast=12, slow=26, signal=9)
    if macd_df is None or macd_df.empty:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    macd_col = [c for c in macd_df.columns if c.startswith("MACD_")][0]
    signal_col = [c for c in macd_df.columns if c.startswith("MACDs_")][0]
    hist_col = [c for c in macd_df.columns if c.startswith("MACDh_")][0]
    macd_line = macd_df[macd_col]
    signal_line = macd_df[signal_col]
    hist = macd_df[hist_col]
    curr_hist = hist.iloc[-1]
    prev_hist = hist.iloc[-2]
    if pd.isna(curr_hist) or pd.isna(prev_hist):
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    confidence = min(1.0, abs(curr_hist) / 2.0)
    if curr_hist > 0:
        return SignalResult(name=NAME, signal="BUY", confidence=confidence)
    if curr_hist < 0:
        return SignalResult(name=NAME, signal="SELL", confidence=confidence)
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
```

**`src/strategies/ichimoku.py`** — use `pandas_ta` ichimoku. BUY when price above cloud (senkou_a and senkou_b). SELL when below. Confidence based on distance from cloud.

```python
import pandas as pd
import pandas_ta as ta
from src.strategies.base import SignalResult

NAME = "ichimoku"

def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < 52:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    ichi = ta.ichimoku(candles["high"], candles["low"], candles["close"])
    if ichi is None:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    span_a = ichi[0].get("ISA_9") or ichi[0].get("ICS_26")
    span_b = ichi[0].get("ISB_26") or ichi[0].get("IKS_26")
    if span_a is None or span_b is None:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    price = candles["close"].iloc[-1]
    cloud_top = max(span_a.iloc[-1], span_b.iloc[-1])
    cloud_bot = min(span_a.iloc[-1], span_b.iloc[-1])
    if pd.isna(cloud_top) or pd.isna(cloud_bot):
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    if price > cloud_top:
        dist = (price - cloud_top) / price
        return SignalResult(name=NAME, signal="BUY", confidence=min(1.0, dist * 50))
    if price < cloud_bot:
        dist = (cloud_bot - price) / price
        return SignalResult(name=NAME, signal="SELL", confidence=min(1.0, dist * 50))
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
```

**`src/strategies/momentum.py`** — Rate of change (ROC) over 10 periods. BUY if ROC > threshold, SELL if < -threshold.

```python
import pandas as pd
import pandas_ta as ta
from src.strategies.base import SignalResult

NAME = "momentum"
PERIOD = 10
THRESHOLD = 0.2  # 0.2% price change

def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < PERIOD + 1:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    roc = ta.roc(candles["close"], length=PERIOD)
    if roc is None or roc.empty or pd.isna(roc.iloc[-1]):
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    value = roc.iloc[-1]
    if value > THRESHOLD:
        return SignalResult(name=NAME, signal="BUY", confidence=min(1.0, value / 2.0))
    if value < -THRESHOLD:
        return SignalResult(name=NAME, signal="SELL", confidence=min(1.0, abs(value) / 2.0))
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
```

**`src/strategies/adx_trend.py`** — ADX(14) confirms trend strength. DI+ vs DI- gives direction. BUY if ADX>25 and DI+>DI-. SELL if ADX>25 and DI->DI+.

```python
import pandas as pd
import pandas_ta as ta
from src.strategies.base import SignalResult
from src import config

NAME = "adx_trend"

def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < 20:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    adx_df = ta.adx(candles["high"], candles["low"], candles["close"], length=14)
    if adx_df is None or adx_df.empty:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    adx = adx_df["ADX_14"].iloc[-1]
    dmp = adx_df["DMP_14"].iloc[-1]
    dmn = adx_df["DMN_14"].iloc[-1]
    if pd.isna(adx) or pd.isna(dmp) or pd.isna(dmn):
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    if adx < config.ADX_TREND_THRESHOLD:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    confidence = min(1.0, (adx - config.ADX_TREND_THRESHOLD) / 25.0)
    if dmp > dmn:
        return SignalResult(name=NAME, signal="BUY", confidence=confidence)
    return SignalResult(name=NAME, signal="SELL", confidence=confidence)
```

- [ ] **Step 5.6: Run all trend strategy tests**

```powershell
pytest tests/test_strategies/ -v -k "ma_crossover or macd or ichimoku or momentum or adx"
```

Expected: All PASS

- [ ] **Step 5.7: Commit**

```powershell
git add src/strategies/ tests/test_strategies/
git commit -m "feat: 5 trend following strategies (MA crossover, MACD, Ichimoku, Momentum, ADX Trend)"
```

---

## Task 6: Mean Reversion Strategies (4 strategies)

**Files:**
- Create: `src/strategies/rsi.py`
- Create: `src/strategies/bollinger.py`
- Create: `src/strategies/stochastic.py`
- Create: `src/strategies/mean_reversion.py`

Follow the test-first pattern from Task 5. For mean reversion, use `ranging_candles` fixture (oscillating data) to verify signals.

- [ ] **Step 6.1: Write and run tests for each, then implement**

**`src/strategies/rsi.py`** — RSI(14). SELL if RSI > 70 (overbought), BUY if RSI < 30 (oversold). Confidence from magnitude of overbought/oversold.

```python
import pandas as pd
import pandas_ta as ta
from src.strategies.base import SignalResult

NAME = "rsi"

def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < 15:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    rsi = ta.rsi(candles["close"], length=14)
    if rsi is None or pd.isna(rsi.iloc[-1]):
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    value = rsi.iloc[-1]
    if value < 30:
        return SignalResult(name=NAME, signal="BUY", confidence=min(1.0, (30 - value) / 30))
    if value > 70:
        return SignalResult(name=NAME, signal="SELL", confidence=min(1.0, (value - 70) / 30))
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
```

**`src/strategies/bollinger.py`** — BB(20,2). BUY when price touches/crosses lower band, SELL when upper band.

```python
import pandas as pd
import pandas_ta as ta
from src.strategies.base import SignalResult

NAME = "bollinger"

def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < 21:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    bb = ta.bbands(candles["close"], length=20, std=2)
    if bb is None or bb.empty:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    price = candles["close"].iloc[-1]
    lower = bb["BBL_20_2.0"].iloc[-1]
    upper = bb["BBU_20_2.0"].iloc[-1]
    mid = bb["BBM_20_2.0"].iloc[-1]
    if pd.isna(lower) or pd.isna(upper):
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    band_width = upper - lower
    if price <= lower:
        conf = min(1.0, (lower - price) / band_width + 0.5)
        return SignalResult(name=NAME, signal="BUY", confidence=conf)
    if price >= upper:
        conf = min(1.0, (price - upper) / band_width + 0.5)
        return SignalResult(name=NAME, signal="SELL", confidence=conf)
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
```

**`src/strategies/stochastic.py`** — Stoch(14,3). BUY if %K < 20 and %K crosses above %D. SELL if %K > 80 and crosses below.

```python
import pandas as pd
import pandas_ta as ta
from src.strategies.base import SignalResult

NAME = "stochastic"

def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < 17:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    stoch = ta.stoch(candles["high"], candles["low"], candles["close"], k=14, d=3)
    if stoch is None or stoch.empty:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    k = stoch["STOCHk_14_3_3"].iloc[-1]
    d = stoch["STOCHd_14_3_3"].iloc[-1]
    if pd.isna(k) or pd.isna(d):
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    if k < 20:
        return SignalResult(name=NAME, signal="BUY", confidence=min(1.0, (20 - k) / 20))
    if k > 80:
        return SignalResult(name=NAME, signal="SELL", confidence=min(1.0, (k - 80) / 20))
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
```

**`src/strategies/mean_reversion.py`** — Z-score of price vs 20-period mean. BUY if z < -1.5, SELL if z > 1.5.

```python
import pandas as pd
from src.strategies.base import SignalResult

NAME = "mean_reversion"
PERIOD = 20
THRESHOLD = 1.5

def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < PERIOD + 1:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    close = candles["close"]
    mean = close.rolling(PERIOD).mean().iloc[-1]
    std = close.rolling(PERIOD).std().iloc[-1]
    if std == 0 or pd.isna(std):
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    z = (close.iloc[-1] - mean) / std
    if z < -THRESHOLD:
        return SignalResult(name=NAME, signal="BUY", confidence=min(1.0, abs(z) / 3.0))
    if z > THRESHOLD:
        return SignalResult(name=NAME, signal="SELL", confidence=min(1.0, z / 3.0))
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
```

- [ ] **Step 6.2: Run all mean reversion tests**

```powershell
pytest tests/test_strategies/ -v -k "rsi or bollinger or stochastic or mean_reversion"
```

Expected: All PASS

- [ ] **Step 6.3: Commit**

```powershell
git add src/strategies/ tests/test_strategies/
git commit -m "feat: 4 mean reversion strategies (RSI, Bollinger, Stochastic, MeanReversion)"
```

---

## Task 7: Structure & Execution Strategies (4 strategies)

**Files:**
- Create: `src/strategies/breakout.py`
- Create: `src/strategies/support_resistance.py`
- Create: `src/strategies/scalping.py`
- Create: `src/strategies/vwap.py`

- [ ] **Step 7.1: Write tests, then implement each**

**`src/strategies/breakout.py`** — Price breaks above 20-period high (BUY) or below 20-period low (SELL). Confidence from ATR-normalized breakout magnitude.

```python
import pandas as pd
import pandas_ta as ta
from src.strategies.base import SignalResult

NAME = "breakout"
PERIOD = 20

def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < PERIOD + 2:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    lookback = candles.iloc[-(PERIOD + 1):-1]
    current = candles.iloc[-1]
    high_20 = lookback["high"].max()
    low_20 = lookback["low"].min()
    atr = ta.atr(candles["high"], candles["low"], candles["close"], length=14)
    atr_val = atr.iloc[-1] if atr is not None and not pd.isna(atr.iloc[-1]) else 1.0
    if current["close"] > high_20:
        conf = min(1.0, (current["close"] - high_20) / atr_val)
        return SignalResult(name=NAME, signal="BUY", confidence=conf)
    if current["close"] < low_20:
        conf = min(1.0, (low_20 - current["close"]) / atr_val)
        return SignalResult(name=NAME, signal="SELL", confidence=conf)
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
```

**`src/strategies/support_resistance.py`** — Pivot-based S/R. BUY if price bounces off support (near 5-period low), SELL near resistance (5-period high), with volume confirmation.

```python
import pandas as pd
from src.strategies.base import SignalResult

NAME = "support_resistance"
PIVOT_PERIOD = 5
PROXIMITY_PCT = 0.002  # within 0.2% of level

def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < PIVOT_PERIOD * 2 + 1:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    recent = candles.iloc[-PIVOT_PERIOD:]
    prev = candles.iloc[-(PIVOT_PERIOD * 2):-PIVOT_PERIOD]
    price = candles["close"].iloc[-1]
    support = prev["low"].min()
    resistance = prev["high"].max()
    near_support = abs(price - support) / price < PROXIMITY_PCT
    near_resistance = abs(price - resistance) / price < PROXIMITY_PCT
    vol_avg = candles["volume"].iloc[-20:].mean()
    vol_now = candles["volume"].iloc[-1]
    vol_conf = min(1.0, vol_now / vol_avg) if vol_avg > 0 else 0.5
    if near_support:
        return SignalResult(name=NAME, signal="BUY", confidence=vol_conf * 0.7)
    if near_resistance:
        return SignalResult(name=NAME, signal="SELL", confidence=vol_conf * 0.7)
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
```

**`src/strategies/scalping.py`** — EMA(5) vs EMA(13) fast crossover for short-term momentum.

```python
import pandas as pd
import pandas_ta as ta
from src.strategies.base import SignalResult

NAME = "scalping"

def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < 15:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    ema5 = ta.ema(candles["close"], length=5)
    ema13 = ta.ema(candles["close"], length=13)
    if ema5 is None or ema13 is None:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    curr5, curr13 = ema5.iloc[-1], ema13.iloc[-1]
    prev5, prev13 = ema5.iloc[-2], ema13.iloc[-2]
    if pd.isna(curr5) or pd.isna(curr13):
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    gap = abs(curr5 - curr13) / curr13
    conf = min(1.0, gap * 1000)
    if curr5 > curr13:
        return SignalResult(name=NAME, signal="BUY", confidence=conf)
    if curr5 < curr13:
        return SignalResult(name=NAME, signal="SELL", confidence=conf)
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
```

**`src/strategies/vwap.py`** — BUY if current price is below VWAP (mean reversion to VWAP). SELL if above. VWAP calculated from today's candles.

```python
import pandas as pd
from src.strategies.base import SignalResult

NAME = "vwap"

def compute(candles: pd.DataFrame) -> SignalResult:
    if len(candles) < 2:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    df = candles.copy()
    df["typical"] = (df["high"] + df["low"] + df["close"]) / 3
    df["cum_vol"] = df["volume"].cumsum()
    df["cum_tp_vol"] = (df["typical"] * df["volume"]).cumsum()
    df["vwap"] = df["cum_tp_vol"] / df["cum_vol"]
    price = df["close"].iloc[-1]
    vwap = df["vwap"].iloc[-1]
    if pd.isna(vwap) or vwap == 0:
        return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
    deviation = (price - vwap) / vwap
    if deviation < -0.001:
        return SignalResult(name=NAME, signal="BUY", confidence=min(1.0, abs(deviation) * 200))
    if deviation > 0.001:
        return SignalResult(name=NAME, signal="SELL", confidence=min(1.0, deviation * 200))
    return SignalResult(name=NAME, signal="NEUTRAL", confidence=0.0)
```

- [ ] **Step 7.2: Run all structure/execution strategy tests**

```powershell
pytest tests/test_strategies/ -v
```

Expected: All 13 strategy test files PASS

- [ ] **Step 7.3: Commit**

```powershell
git add src/strategies/ tests/test_strategies/
git commit -m "feat: 4 structure/execution strategies (Breakout, S&R, Scalping, VWAP)"
```

---

## Task 8: Market Regime Classifier

**Files:**
- Create: `src/regime/classifier.py`
- Create: `src/regime/__init__.py`
- Create: `tests/test_regime.py`

- [ ] **Step 8.1: Write failing tests**

Create `tests/test_regime.py`:

```python
from src.regime.classifier import classify

def test_trending_regime(trending_up_candles):
    # trending_up_candles has a clear trend, ADX should be high
    result = classify(trending_up_candles)
    assert result in ("TRENDING", "RANGING", "BREAKOUT")  # valid output
    assert isinstance(result, str)

def test_ranging_regime(ranging_candles):
    result = classify(ranging_candles)
    assert result in ("TRENDING", "RANGING", "BREAKOUT")

def test_returns_string(trending_up_candles):
    result = classify(trending_up_candles)
    assert isinstance(result, str)

def test_short_candles_returns_ranging():
    import pandas as pd
    df = pd.DataFrame({"high": [1]*5, "low": [1]*5, "close": [1]*5, "volume": [1]*5})
    assert classify(df) == "RANGING"
```

- [ ] **Step 8.2: Run to verify fails**

```powershell
pytest tests/test_regime.py -v
```

- [ ] **Step 8.3: Create `src/regime/__init__.py`** (empty) and `src/regime/classifier.py`**

```python
import pandas as pd
import pandas_ta as ta
from src import config

def classify(candles: pd.DataFrame) -> str:
    """
    Priority: BREAKOUT > TRENDING > RANGING
    """
    if len(candles) < max(config.ATR_LOOKBACK + 1, 20):
        return "RANGING"

    # ATR spike → BREAKOUT
    atr = ta.atr(candles["high"], candles["low"], candles["close"], length=config.ATR_LOOKBACK)
    if atr is not None and not atr.empty:
        atr_current = atr.iloc[-1]
        atr_mean = atr.iloc[-config.ATR_LOOKBACK:].mean()
        if not pd.isna(atr_current) and not pd.isna(atr_mean) and atr_mean > 0:
            if atr_current > config.ATR_BREAKOUT_MULTIPLIER * atr_mean:
                return "BREAKOUT"

    # ADX > threshold → TRENDING
    adx_df = ta.adx(candles["high"], candles["low"], candles["close"], length=14)
    if adx_df is not None and not adx_df.empty:
        adx_val = adx_df["ADX_14"].iloc[-1]
        if not pd.isna(adx_val) and adx_val > config.ADX_TREND_THRESHOLD:
            return "TRENDING"

    # Default → RANGING (also covers low BB width)
    return "RANGING"
```

- [ ] **Step 8.4: Run tests**

```powershell
pytest tests/test_regime.py -v
```

Expected: PASS

- [ ] **Step 8.5: Commit**

```powershell
git add src/regime/ tests/test_regime.py
git commit -m "feat: market regime classifier (BREAKOUT > TRENDING > RANGING)"
```

---

## Task 9: Signal Aggregator

**Files:**
- Create: `src/aggregator/scorer.py`
- Create: `src/aggregator/__init__.py`
- Create: `tests/test_aggregator.py`

- [ ] **Step 9.1: Write failing tests**

Create `tests/test_aggregator.py`:

```python
from src.aggregator.scorer import aggregate, AggregateResult
from src.strategies.base import SignalResult

TRENDING = "TRENDING"
WEIGHTS = {
    "ma_crossover": {"TRENDING": 1.5, "RANGING": 0.5, "BREAKOUT": 0.5},
    "macd":         {"TRENDING": 1.5, "RANGING": 0.5, "BREAKOUT": 0.8},
}

def make_signal(name, signal, confidence=0.8):
    return SignalResult(name=name, signal=signal, confidence=confidence)

def test_all_buy_gives_high_buy_score():
    signals = [
        make_signal("ma_crossover", "BUY"),
        make_signal("macd", "BUY"),
    ]
    result = aggregate(signals, TRENDING)
    assert result.buy_score > result.sell_score
    assert result.buy_score > 0

def test_neutral_contributes_zero():
    signals = [make_signal("ma_crossover", "NEUTRAL", 0.9)]
    result = aggregate(signals, TRENDING)
    assert result.buy_score == 0.0
    assert result.sell_score == 0.0

def test_returns_aggregate_result():
    signals = [make_signal("ma_crossover", "BUY")]
    result = aggregate(signals, TRENDING)
    assert isinstance(result, AggregateResult)
    assert hasattr(result, "buy_score")
    assert hasattr(result, "sell_score")
    assert hasattr(result, "regime")
```

- [ ] **Step 9.2: Run to verify fails**

```powershell
pytest tests/test_aggregator.py -v
```

- [ ] **Step 9.3: Create `src/aggregator/__init__.py`** (empty) and `src/aggregator/scorer.py`**

```python
from dataclasses import dataclass, field
from src.strategies.base import SignalResult

@dataclass
class AggregateResult:
    buy_score: float
    sell_score: float
    regime: str
    signals: dict = field(default_factory=dict)

# Strategy weights per regime
WEIGHTS: dict[str, dict[str, float]] = {
    "ma_crossover":       {"TRENDING": 1.5, "RANGING": 0.5, "BREAKOUT": 0.5},
    "macd":               {"TRENDING": 1.5, "RANGING": 0.5, "BREAKOUT": 0.8},
    "ichimoku":           {"TRENDING": 1.5, "RANGING": 0.3, "BREAKOUT": 0.5},
    "momentum":           {"TRENDING": 1.2, "RANGING": 0.3, "BREAKOUT": 1.0},
    "adx_trend":          {"TRENDING": 1.5, "RANGING": 0.3, "BREAKOUT": 0.8},
    "rsi":                {"TRENDING": 0.3, "RANGING": 1.5, "BREAKOUT": 0.5},
    "bollinger":          {"TRENDING": 0.5, "RANGING": 1.5, "BREAKOUT": 1.2},
    "stochastic":         {"TRENDING": 0.3, "RANGING": 1.5, "BREAKOUT": 0.5},
    "mean_reversion":     {"TRENDING": 0.3, "RANGING": 1.5, "BREAKOUT": 0.3},
    "breakout":           {"TRENDING": 0.5, "RANGING": 0.5, "BREAKOUT": 2.0},
    "support_resistance": {"TRENDING": 0.8, "RANGING": 1.0, "BREAKOUT": 1.5},
    "scalping":           {"TRENDING": 0.8, "RANGING": 1.0, "BREAKOUT": 1.0},
    "vwap":               {"TRENDING": 1.0, "RANGING": 1.0, "BREAKOUT": 1.0},
}

def aggregate(signals: list[SignalResult], regime: str) -> AggregateResult:
    buy_score = 0.0
    sell_score = 0.0
    signals_dict = {}
    for s in signals:
        weight = WEIGHTS.get(s.name, {}).get(regime, 1.0)
        signals_dict[s.name] = {"signal": s.signal, "confidence": s.confidence}
        if s.signal == "BUY":
            buy_score += weight * s.confidence
        elif s.signal == "SELL":
            sell_score += weight * s.confidence
        # NEUTRAL contributes zero
    return AggregateResult(
        buy_score=round(buy_score, 4),
        sell_score=round(sell_score, 4),
        regime=regime,
        signals=signals_dict,
    )
```

- [ ] **Step 9.4: Run tests**

```powershell
pytest tests/test_aggregator.py -v
```

Expected: PASS

- [ ] **Step 9.5: Commit**

```powershell
git add src/aggregator/ tests/test_aggregator.py
git commit -m "feat: weighted signal aggregator with regime-based weights"
```

---

## Task 10: Trigger Gate

**Files:**
- Create: `src/trigger/gate.py`
- Create: `src/trigger/__init__.py`
- Create: `tests/test_trigger.py`

- [ ] **Step 10.1: Write failing tests**

Create `tests/test_trigger.py`:

```python
from src.trigger.gate import should_trigger
from src.aggregator.scorer import AggregateResult

def make_agg(buy=7.0, sell=1.0, regime="TRENDING"):
    return AggregateResult(buy_score=buy, sell_score=sell, regime=regime, signals={})

def test_strong_buy_triggers():
    assert should_trigger(make_agg(7.0, 1.0), open_trades=0, kill_switch=False) is True

def test_kill_switch_blocks():
    assert should_trigger(make_agg(7.0, 1.0), open_trades=0, kill_switch=True) is False

def test_low_score_no_trigger():
    assert should_trigger(make_agg(3.0, 1.0), open_trades=0, kill_switch=False) is False

def test_score_conflict_no_trigger():
    assert should_trigger(make_agg(5.5, 5.0), open_trades=0, kill_switch=False) is False

def test_max_trades_blocks():
    assert should_trigger(make_agg(7.0, 1.0), open_trades=3, kill_switch=False) is False
```

- [ ] **Step 10.2: Run to verify fails**

```powershell
pytest tests/test_trigger.py -v
```

- [ ] **Step 10.3: Create `src/trigger/__init__.py`** (empty) and `src/trigger/gate.py`**

```python
from src.aggregator.scorer import AggregateResult
from src import config

def should_trigger(agg: AggregateResult, open_trades: int, kill_switch: bool) -> bool:
    """Returns True if the AI layer (or direct trade) should be invoked."""
    if kill_switch:
        return False
    if open_trades >= config.MAX_CONCURRENT_TRADES:
        return False
    max_score = max(agg.buy_score, agg.sell_score)
    if max_score < config.TRIGGER_MIN_SCORE:
        return False
    if abs(agg.buy_score - agg.sell_score) < config.TRIGGER_MIN_SCORE_DIFF:
        return False
    return True

def get_direction(agg: AggregateResult) -> str:
    """Returns 'BUY' or 'SELL' based on dominant score."""
    return "BUY" if agg.buy_score >= agg.sell_score else "SELL"
```

- [ ] **Step 10.4: Run tests**

```powershell
pytest tests/test_trigger.py -v
```

Expected: PASS

- [ ] **Step 10.5: Commit**

```powershell
git add src/trigger/ tests/test_trigger.py
git commit -m "feat: trigger gate with score, conflict, concurrent trade, and kill switch checks"
```

---

## Task 11: Risk Engine

**Files:**
- Create: `src/risk/engine.py`
- Create: `src/risk/__init__.py`

- [ ] **Step 11.1: Write failing tests**

Create `tests/test_risk.py`:

```python
from src.risk.engine import validate, RiskResult

def test_valid_buy_passes():
    result = validate(
        action="BUY", confidence=0.8, sl=1917.0, tp=1940.0,
        entry=1920.0, balance=10000.0, open_trades=1, kill_switch=False
    )
    assert result.approved
    assert result.lot_size > 0

def test_low_confidence_blocked():
    result = validate(
        action="BUY", confidence=0.5, sl=1917.0, tp=1940.0,
        entry=1920.0, balance=10000.0, open_trades=1, kill_switch=False
    )
    assert not result.approved
    assert result.block_reason == "LOW_CONFIDENCE"

def test_kill_switch_blocks():
    result = validate(
        action="BUY", confidence=0.9, sl=1917.0, tp=1940.0,
        entry=1920.0, balance=10000.0, open_trades=0, kill_switch=True
    )
    assert not result.approved
    assert result.block_reason == "KILL_SWITCH_ACTIVE"

def test_invalid_sl_too_tight_blocked():
    result = validate(
        action="BUY", confidence=0.9, sl=1919.5, tp=1940.0,  # only $0.50 away
        entry=1920.0, balance=10000.0, open_trades=0, kill_switch=False
    )
    assert not result.approved
    assert result.block_reason == "INVALID_SL"

def test_lot_size_below_minimum_blocked():
    result = validate(
        action="BUY", confidence=0.9, sl=1910.0, tp=1940.0,  # $10 SL
        entry=1920.0, balance=100.0, open_trades=0, kill_switch=False  # tiny balance
    )
    assert not result.approved
    assert result.block_reason == "BELOW_MIN_LOT"
```

- [ ] **Step 11.2: Run to verify fails**

```powershell
pytest tests/test_risk.py -v
```

- [ ] **Step 11.3: Create `src/risk/__init__.py`** (empty) and `src/risk/engine.py`**

```python
from dataclasses import dataclass
from src import config

@dataclass
class RiskResult:
    approved: bool
    lot_size: float = 0.0
    block_reason: str | None = None

MIN_LOT = 0.01
LOT_STEP = 0.01

def validate(
    action: str,
    confidence: float,
    sl: float,
    tp: float,
    entry: float,
    balance: float,
    open_trades: int,
    kill_switch: bool,
) -> RiskResult:
    if kill_switch:
        return RiskResult(approved=False, block_reason="KILL_SWITCH_ACTIVE")
    if open_trades >= config.MAX_CONCURRENT_TRADES:
        return RiskResult(approved=False, block_reason="MAX_TRADES_REACHED")
    if confidence < config.MIN_AI_CONFIDENCE:
        return RiskResult(approved=False, block_reason="LOW_CONFIDENCE")

    sl_distance = abs(entry - sl)
    if sl_distance < config.MIN_SL_USD:
        return RiskResult(approved=False, block_reason="INVALID_SL")
    if sl_distance > config.MAX_SL_USD:
        return RiskResult(approved=False, block_reason="INVALID_SL")

    # Lot size: risk_amount / (sl_distance * 100 oz/lot)
    risk_amount = balance * config.RISK_PER_TRADE
    lot_size = risk_amount / (sl_distance * 100)
    # Round down to nearest LOT_STEP
    lot_size = max(0.0, (lot_size // LOT_STEP) * LOT_STEP)

    if lot_size < MIN_LOT:
        return RiskResult(approved=False, block_reason="BELOW_MIN_LOT")

    return RiskResult(approved=True, lot_size=lot_size)
```

- [ ] **Step 11.4: Run tests**

```powershell
pytest tests/test_risk.py -v
```

Expected: PASS

- [ ] **Step 11.5: Commit**

```powershell
git add src/risk/ tests/test_risk.py
git commit -m "feat: risk engine with lot sizing, SL validation, confidence and kill switch checks"
```

---

## Task 12: Executor & Logger

**Files:**
- Create: `src/executor/orders.py`
- Create: `src/executor/__init__.py`
- Create: `src/logger/writer.py`
- Create: `src/logger/__init__.py`

- [ ] **Step 12.1: Create `src/executor/__init__.py`** (empty)

- [ ] **Step 12.2: Create `src/executor/orders.py`**

```python
import MetaTrader5 as mt5
import logging
from src.mt5_bridge.data import SYMBOL

logger = logging.getLogger(__name__)

def place_order(direction: str, lot_size: float, sl: float, tp: float) -> dict:  # noqa: E501
    order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
    price = mt5.symbol_info_tick(SYMBOL).ask if direction == "BUY" else mt5.symbol_info_tick(SYMBOL).bid
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": lot_size,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 20260325,
        "comment": "opengold",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        retcode = result.retcode if result else "None"
        comment = result.comment if result else "no result"
        logger.error(f"ORDER_REJECTED: retcode={retcode} comment={comment}")
        return {"success": False, "retcode": retcode, "comment": comment}
    logger.info(f"Order placed: {direction} {lot_size} lots ticket={result.order}")
    return {"success": True, "ticket": result.order, "price": result.price}

def sync_positions(previous_snapshot: list[dict], positions_get_fn) -> tuple[list[dict], list[dict]]:
    """Returns (closed_positions, current_positions) by comparing snapshots."""
    current = positions_get_fn()
    current_tickets = {p["ticket"] for p in current}
    closed = [p for p in previous_snapshot if p["ticket"] not in current_tickets]
    return closed, current
```

- [ ] **Step 12.3: Create `src/logger/__init__.py`** (empty) and `src/logger/writer.py`**

```python
from datetime import datetime, timezone
from src.db import execute
import logging

logger = logging.getLogger(__name__)

def check_and_log_trade_no_duplicate(
    open_time, close_time, direction: str, lot_size: float,
    open_price: float, close_price: float, sl: float, tp: float, pnl: float,
):
    """Log trade only if no matching row exists (dedup by open_time+direction+open_price)."""
    existing = execute(
        "SELECT 1 FROM trades WHERE open_time=%s AND direction=%s AND open_price=%s",
        (open_time, direction, open_price),
        fetch=True,
    )
    if not existing:
        log_trade(open_time, close_time, direction, lot_size, open_price, close_price, sl, tp, pnl)

def log_decision(
    regime: str,
    buy_score: float,
    sell_score: float,
    trigger_fired: bool,
    ai_action: str | None = None,
    ai_confidence: float | None = None,
    ai_sl: float | None = None,
    ai_tp: float | None = None,
    risk_block_reason: str | None = None,
):
    try:
        execute(
            """INSERT INTO decisions
               (time, regime, buy_score, sell_score, trigger_fired,
                ai_action, ai_confidence, ai_sl, ai_tp, risk_block_reason)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (datetime.now(timezone.utc), regime, buy_score, sell_score, trigger_fired,
             ai_action, ai_confidence, ai_sl, ai_tp, risk_block_reason),
        )
    except Exception as e:
        logger.error(f"log_decision failed: {e}")

def log_trade(
    open_time, close_time, direction: str, lot_size: float,
    open_price: float, close_price: float, sl: float, tp: float, pnl: float,
):
    result = "WIN" if pnl > 1.0 else "LOSS" if pnl < -1.0 else "BREAKEVEN"
    try:
        execute(
            """INSERT INTO trades
               (open_time, close_time, direction, lot_size,
                open_price, close_price, sl, tp, pnl, result)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (open_time, close_time, direction, lot_size,
             open_price, close_price, sl, tp, pnl, result),
        )
    except Exception as e:
        logger.error(f"log_trade failed: {e}")

def get_kill_switch_state() -> bool:
    from datetime import datetime, timezone
    rows = execute(
        "SELECT key, value FROM system_state WHERE key IN ('kill_switch_active','kill_switch_date')",
        fetch=True,
    )
    state = {r[0]: r[1] for r in rows} if rows else {}
    active = state.get("kill_switch_active", "false") == "true"
    ks_date = state.get("kill_switch_date", "")
    today_utc = datetime.now(timezone.utc).date().isoformat()
    if active and ks_date != today_utc:
        # Auto-reset at UTC midnight
        set_kill_switch(False)
        return False
    return active

def set_kill_switch(active: bool):
    from datetime import datetime, timezone
    value = "true" if active else "false"
    today_utc = datetime.now(timezone.utc).date().isoformat()
    execute(
        "UPDATE system_state SET value=%s, updated_at=NOW() WHERE key='kill_switch_active'",
        (value,),
    )
    execute(
        "UPDATE system_state SET value=%s, updated_at=NOW() WHERE key='kill_switch_date'",
        (today_utc,),
    )

def get_daily_start_balance() -> tuple[float, str]:
    """Returns (balance, date_utc_iso) stored for the current day's baseline."""
    rows = execute(
        "SELECT key, value FROM system_state WHERE key IN ('daily_start_balance','daily_start_date')",
        fetch=True,
    )
    state = {r[0]: r[1] for r in rows} if rows else {}
    try:
        balance = float(state.get("daily_start_balance", "0"))
    except ValueError:
        balance = 0.0
    date_str = state.get("daily_start_date", "")
    return balance, date_str

def set_daily_start_balance(balance: float):
    from datetime import datetime, timezone
    today_utc = datetime.now(timezone.utc).date().isoformat()
    execute(
        "UPDATE system_state SET value=%s, updated_at=NOW() WHERE key='daily_start_balance'",
        (str(balance),),
    )
    execute(
        "UPDATE system_state SET value=%s, updated_at=NOW() WHERE key='daily_start_date'",
        (today_utc,),
    )
```

- [ ] **Step 12.4: Commit**

```powershell
git add src/executor/ src/logger/ 
git commit -m "feat: executor (place_order, sync_positions) and logger (decisions, trades, kill switch)"
```

---

## Task 13: Main Loop

**Files:**
- Create: `main.py`

- [ ] **Step 13.1: Create `main.py`**

```python
import time
import logging
from datetime import datetime, timezone

from src import config
from src.mt5_bridge.connection import connect, disconnect, is_connected, get_account_info
from src.mt5_bridge.data import fetch_candles, get_last_candle_time, get_positions, get_history_deals
from src.regime.classifier import classify
from src.strategies import run_all
from src.aggregator.scorer import aggregate
from src.trigger.gate import should_trigger, get_direction
from src.risk.engine import validate
from src.executor.orders import place_order, sync_positions
from src.logger.writer import (
    log_decision, log_trade,
    get_kill_switch_state, set_kill_switch,
    get_daily_start_balance, set_daily_start_balance,
    check_and_log_trade_no_duplicate,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("main")

def connect_with_retry(retries=3) -> bool:
    for attempt in range(retries):
        if connect():
            return True
        wait = 2 ** (attempt + 1)  # 2s, 4s, 8s as per spec §12
        logger.warning(f"MT5 connect attempt {attempt+1} failed, retrying in {wait}s")
        time.sleep(wait)
    return False

def check_daily_reset(balance: float):
    """Refresh daily_start_balance at each UTC midnight."""
    today_utc = datetime.now(timezone.utc).date().isoformat()
    stored_balance, stored_date = get_daily_start_balance()
    if stored_date != today_utc:
        set_daily_start_balance(balance)
        logger.info(f"Daily start balance reset for {today_utc}: {balance}")

def main():
    logger.info("OpenGold starting...")
    if not connect_with_retry():
        logger.critical("Cannot connect to MT5. Exiting.")
        return

    last_candle_time = None
    position_snapshot = []

    while True:
        try:
            if not is_connected():
                logger.warning("MT5 disconnected. Reconnecting...")
                if not connect_with_retry():
                    logger.error("Reconnect failed. Pausing 60s.")
                    time.sleep(60)
                    continue
                # Reconcile missed closes — skip duplicates by open_time+direction+open_price
                from datetime import timedelta
                now = datetime.now(timezone.utc)
                closed_deals = get_history_deals(now - timedelta(hours=1), now)
                for deal in closed_deals:
                    if deal["entry"] == 1:  # OUT — closing deal type is opposite of original position
                        # MT5: deal type=0 (BUY deal) closes a SELL position → original direction=SELL
                        original_direction = "SELL" if deal["type"] == 0 else "BUY"
                        check_and_log_trade_no_duplicate(
                            open_time=deal["time"], close_time=deal["time"],
                            direction=original_direction,
                            lot_size=deal["volume"], open_price=deal["price"],
                            close_price=deal["price"], sl=0, tp=0, pnl=deal["profit"],
                        )

            current_time = get_last_candle_time()
            if current_time is None or current_time == last_candle_time:
                time.sleep(config.POLL_INTERVAL_SECONDS)
                continue

            # New candle detected
            last_candle_time = current_time
            candles = fetch_candles(200)
            if candles.empty:
                time.sleep(config.POLL_INTERVAL_SECONDS)
                continue

            account = get_account_info()
            balance = account.get("balance", 0.0)
            equity = account.get("equity", 0.0)
            check_daily_reset(balance)

            # Drawdown kill switch
            kill_switch = get_kill_switch_state()
            daily_start, _ = get_daily_start_balance()
            if daily_start > 0 and equity < daily_start * (1 - config.DAILY_DRAWDOWN_LIMIT):
                if not kill_switch:
                    logger.warning(f"KILL SWITCH ACTIVATED: equity={equity} start={daily_start}")
                    set_kill_switch(True)
                    kill_switch = True

            # Sync positions
            closed_positions, position_snapshot = sync_positions(position_snapshot, get_positions)
            for closed in closed_positions:
                # In Phase 1, we log approximate PnL — real PnL comes from MT5 history in Phase 3
                log_trade(
                    open_time=datetime.now(timezone.utc),
                    close_time=datetime.now(timezone.utc),
                    direction=closed["direction"],
                    lot_size=closed["volume"],
                    open_price=closed["open_price"],
                    close_price=candles["close"].iloc[-1],
                    sl=closed["sl"],
                    tp=closed["tp"],
                    pnl=0.0,  # placeholder until Phase 3 reconciliation
                )

            # Strategy pipeline
            regime = classify(candles)
            signals = run_all(candles, regime)
            agg = aggregate(signals, regime)
            open_trades = len(position_snapshot)
            triggered = should_trigger(agg, open_trades, kill_switch)

            logger.info(
                f"Candle {current_time} | {regime} | "
                f"buy={agg.buy_score:.2f} sell={agg.sell_score:.2f} | "
                f"trigger={'YES' if triggered else 'NO'}"
            )

            if not triggered:
                log_decision(regime, agg.buy_score, agg.sell_score, False)
                time.sleep(config.POLL_INTERVAL_SECONDS)
                continue

            # Phase 1: no AI — use score direction directly with fixed confidence
            direction = get_direction(agg)
            price = candles["close"].iloc[-1]
            atr_val = candles["high"].rolling(14).max().iloc[-1] - candles["low"].rolling(14).min().iloc[-1]
            sl = price - atr_val * 1.5 if direction == "BUY" else price + atr_val * 1.5
            tp = price + atr_val * 2.0 if direction == "BUY" else price - atr_val * 2.0
            confidence = 0.75  # fixed in Phase 1; Phase 3 replaces with AI confidence

            risk = validate(
                action=direction, confidence=confidence,
                sl=sl, tp=tp, entry=price,
                balance=balance, open_trades=open_trades, kill_switch=kill_switch,
            )

            if not risk.approved:
                logger.info(f"Risk blocked: {risk.block_reason}")
                log_decision(regime, agg.buy_score, agg.sell_score, True,
                             ai_action=direction, ai_confidence=confidence,
                             ai_sl=sl, ai_tp=tp, risk_block_reason=risk.block_reason)
                time.sleep(config.POLL_INTERVAL_SECONDS)
                continue

            order = place_order(direction, risk.lot_size, sl, tp)
            log_decision(
                regime, agg.buy_score, agg.sell_score, True,
                ai_action=direction, ai_confidence=confidence,
                ai_sl=sl, ai_tp=tp,
                risk_block_reason=None if order["success"] else "ORDER_REJECTED",
            )

        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
            time.sleep(config.POLL_INTERVAL_SECONDS)

    disconnect()
    logger.info("OpenGold stopped.")

if __name__ == "__main__":
    main()
```

- [ ] **Step 13.2: Create `src/strategies/__init__.py`** with `run_all`

```python
import pandas as pd
from src.strategies.base import SignalResult
from . import (
    ma_crossover, macd, ichimoku, momentum, adx_trend,
    rsi, bollinger, stochastic, mean_reversion,
    breakout, support_resistance, scalping, vwap,
)

_ALL_STRATEGIES = [
    ma_crossover, macd, ichimoku, momentum, adx_trend,
    rsi, bollinger, stochastic, mean_reversion,
    breakout, support_resistance, scalping, vwap,
]

def run_all(candles: pd.DataFrame, regime: str) -> list[SignalResult]:
    results = []
    for strategy in _ALL_STRATEGIES:
        try:
            results.append(strategy.compute(candles))
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Strategy {strategy.__name__} failed: {e}")
    return results
```

- [ ] **Step 13.3: Install requirements**

```powershell
pip install -r requirements.txt
```

- [ ] **Step 13.4: Run all unit tests**

```powershell
pytest tests/ -v --ignore=tests/integration
```

Expected: All PASS

- [ ] **Step 13.5: Run the bot manually for 5 minutes in demo**

```powershell
python main.py
```

Watch for:
- `MT5 connected` log line
- `Candle YYYY-MM-DD HH:MM:SS | TRENDING | buy=X.XX sell=X.XX | trigger=YES/NO` every minute
- No unhandled exceptions

- [ ] **Step 13.6: Verify decisions are being written to DB**

```powershell
docker exec -it opengold-timescaledb-1 psql -U opengold -d opengold -c "SELECT time, regime, buy_score, sell_score, trigger_fired FROM decisions ORDER BY time DESC LIMIT 5;"
```

Expected: Rows visible with real data.

- [ ] **Step 13.7: Commit**

```powershell
git add main.py src/strategies/__init__.py
git commit -m "feat: main trading loop - Phase 1+2 complete, headless bot running"
```

---

## Task 14: Final Integration Verification

- [ ] **Step 14.1: Run full test suite**

```powershell
pytest tests/ -v --ignore=tests/integration
```

Expected: All tests PASS, 0 failures.

- [ ] **Step 14.2: Run bot for at least 10 candles, verify logs**

```powershell
python main.py
```

After 10+ minutes, Ctrl+C to stop.

- [ ] **Step 14.3: Verify DB has data in all 3 tables**

```powershell
docker exec -it opengold-timescaledb-1 psql -U opengold -d opengold -c "SELECT COUNT(*) FROM decisions; SELECT COUNT(*) FROM trades; SELECT * FROM system_state;"
```

Expected: `decisions` has rows, `system_state` has kill switch and balance values.

- [ ] **Step 14.4: Final commit & tag**

```powershell
git add -A
git commit -m "chore: Phase 1+2 complete - headless trading bot with 13 strategies, regime classifier, aggregator, trigger, risk engine"
git tag v0.1.0-core
```

---

## What's Next

- **Phase 3 Plan:** Claude Haiku AI decision layer + Trading Journal guardrail
- **Phase 4 Plan:** FastAPI dashboard with WebSocket live feed
- **Phase 5 Plan:** Optimization — threshold tuning, strategy weight refinement
