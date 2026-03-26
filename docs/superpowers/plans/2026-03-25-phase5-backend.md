# Phase 5 Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `signals JSONB` to the decisions schema, update `log_decision()`, build `preflight.py`, and create the FastAPI API layer with 8 endpoints and ~15 tests.

**Architecture:** Schema migration adds `signals JSONB` to `decisions`, `log_decision()` persists per-strategy breakdown via `json.dumps()`, `preflight.py` validates `.env`/DB/MT5 before launch, `src/api/` is a separate FastAPI process (port 8000) that exposes read-only JSON over TimescaleDB + MT5 bridge with a single kill-switch write endpoint.

**Tech Stack:** Python 3.12, FastAPI 0.110.0+, uvicorn, psycopg2-binary, MetaTrader5, pytest + TestClient

**Spec:** `docs/superpowers/specs/2026-03-25-phase5-preflight-dashboard.md`

**Run tests from:** `D:\hobbies\opengold` (project root)

---

## File Map

| Action | File | Purpose |
|--------|------|---------|
| Modify | `src/schema.sql` | Add `signals JSONB` to `CREATE TABLE decisions` + migration comment |
| Modify | `src/logger/writer.py` | Add `signals` param to `log_decision()`, serialize with `json.dumps` |
| Modify | `main.py` | Pass `signals=agg.signals` at all 4 `log_decision()` call sites |
| Modify | `src/config.py` | Add `DASHBOARD_API_PORT`, `DASHBOARD_API_HOST` |
| Modify | `.env.example` | Add `DASHBOARD_API_PORT=8000`, `DASHBOARD_API_HOST=127.0.0.1` |
| Create | `preflight.py` | Launch validator: checks .env, DB, MT5, DRY_RUN |
| Create | `src/api/__init__.py` | Empty marker |
| Create | `src/api/app.py` | FastAPI app with lifespan, CORS, router mounts |
| Create | `src/api/routes/__init__.py` | Empty marker |
| Create | `src/api/routes/candles.py` | GET /api/candles |
| Create | `src/api/routes/account.py` | GET /api/account |
| Create | `src/api/routes/signals.py` | GET /api/signals |
| Create | `src/api/routes/decisions.py` | GET /api/decisions |
| Create | `src/api/routes/trades.py` | GET /api/trades |
| Create | `src/api/routes/stats.py` | GET /api/stats |
| Create | `src/api/routes/status.py` | GET /api/status |
| Create | `src/api/routes/killswitch.py` | POST /api/killswitch |
| Create | `tests/test_api_candles.py` | Tests for /api/candles |
| Create | `tests/test_api_signals.py` | Tests for /api/signals + /api/decisions + /api/trades |
| Create | `tests/test_api_stats.py` | Tests for /api/stats |
| Create | `tests/test_api_status.py` | Tests for /api/status + /api/killswitch |

---

## Task 1: Schema + log_decision + main.py

**Files:**
- Modify: `src/schema.sql`
- Modify: `src/logger/writer.py` (lines 7-31)
- Modify: `main.py` (4 call sites)
- Test: `tests/test_writer.py` (add to existing)

- [ ] **Step 1: Update `src/schema.sql` — add `signals JSONB` to decisions table**

Replace the existing `CREATE TABLE IF NOT EXISTS decisions` block (lines 13-24):

```sql
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
    risk_block_reason TEXT,
    signals           JSONB        -- per-strategy breakdown (added Phase 5)
);
-- For existing databases: ALTER TABLE decisions ADD COLUMN IF NOT EXISTS signals JSONB;
SELECT create_hypertable('decisions', 'time', if_not_exists => TRUE);
```

- [ ] **Step 2: Run the migration on existing DB (one-time)**

```powershell
docker exec -i opengold-db-1 psql -U opengold -d opengold -c "ALTER TABLE decisions ADD COLUMN IF NOT EXISTS signals JSONB;"
```

Expected: `ALTER TABLE` (or `NOTICE: column "signals" already exists` if already run)

- [ ] **Step 3: Write the failing test for signals persistence**

Add to `tests/test_writer.py`:

```python
import json
from unittest.mock import patch, MagicMock

def test_log_decision_persists_signals():
    """log_decision passes signals JSON string to execute()."""
    signals = {"ma_crossover": {"signal": "BUY", "confidence": 0.85}}
    with patch("src.logger.writer.execute") as mock_exec:
        from src.logger.writer import log_decision
        log_decision("TRENDING", 7.5, 1.2, True, signals=signals)
        call_args = mock_exec.call_args[0]
        params = call_args[1]
        # Last param is signals — should be json-serialized string
        assert params[-1] == json.dumps(signals)

def test_log_decision_signals_none_by_default():
    """log_decision passes None for signals when not provided."""
    with patch("src.logger.writer.execute") as mock_exec:
        from src.logger.writer import log_decision
        log_decision("RANGING", 3.0, 4.0, False)
        call_args = mock_exec.call_args[0]
        params = call_args[1]
        assert params[-1] is None
```

- [ ] **Step 4: Run tests to verify they fail**

```powershell
cd D:\hobbies\opengold
python -m pytest tests/test_writer.py::test_log_decision_persists_signals tests/test_writer.py::test_log_decision_signals_none_by_default -v
```

Expected: FAIL — `log_decision()` doesn't accept `signals` kwarg yet

- [ ] **Step 5: Update `src/logger/writer.py` — add `signals` param**

Replace lines 7-31 (the full `log_decision` function):

```python
import json

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
    signals: dict | None = None,
):
    try:
        execute(
            """INSERT INTO decisions
               (time, regime, buy_score, sell_score, trigger_fired,
                ai_action, ai_confidence, ai_sl, ai_tp, risk_block_reason, signals)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                datetime.now(timezone.utc), regime, buy_score, sell_score, trigger_fired,
                ai_action, ai_confidence, ai_sl, ai_tp, risk_block_reason,
                json.dumps(signals) if signals is not None else None,
            ),
        )
    except Exception as e:
        logger.error(f"log_decision failed: {e}")
```

Add `import json` at the top of the file (after `import logging`).

- [ ] **Step 6: Run tests to verify they pass**

```powershell
python -m pytest tests/test_writer.py::test_log_decision_persists_signals tests/test_writer.py::test_log_decision_signals_none_by_default -v
```

Expected: PASS

- [ ] **Step 7: Update `main.py` — pass `signals=agg.signals` at all 4 call sites**

Find the 4 `log_decision(` calls in `run_loop()` and add `signals=agg.signals` to each:

**Call site 1** — trigger not fired:
```python
# FIND:
            if not triggered:
                log_decision(regime, agg.buy_score, agg.sell_score, trigger_fired=False)
# REPLACE WITH:
            if not triggered:
                log_decision(regime, agg.buy_score, agg.sell_score, trigger_fired=False, signals=agg.signals)
```

**Call site 2** — AI SKIP:
```python
# FIND:
            if ai.action == "SKIP" or ai.error:
                log_decision(
                    regime, agg.buy_score, agg.sell_score, trigger_fired=True,
                    ai_action="SKIP", risk_block_reason=ai.error or "AI_SKIP",
                )
# REPLACE WITH:
            if ai.action == "SKIP" or ai.error:
                log_decision(
                    regime, agg.buy_score, agg.sell_score, trigger_fired=True,
                    ai_action="SKIP", risk_block_reason=ai.error or "AI_SKIP",
                    signals=agg.signals,
                )
```

**Call site 3** — risk blocked:
```python
# FIND:
                log_decision(
                    regime, agg.buy_score, agg.sell_score, trigger_fired=True,
                    ai_action=direction, ai_confidence=confidence,
                    ai_sl=sl, ai_tp=tp, risk_block_reason=risk.block_reason,
                )
# REPLACE WITH:
                log_decision(
                    regime, agg.buy_score, agg.sell_score, trigger_fired=True,
                    ai_action=direction, ai_confidence=confidence,
                    ai_sl=sl, ai_tp=tp, risk_block_reason=risk.block_reason,
                    signals=agg.signals,
                )
```

**Call site 4** — order placed/rejected:
```python
# FIND:
            log_decision(
                regime, agg.buy_score, agg.sell_score, trigger_fired=True,
                ai_action=direction, ai_confidence=confidence,
                ai_sl=sl, ai_tp=tp,
                risk_block_reason=None if order["success"] else "ORDER_REJECTED",
            )
# REPLACE WITH:
            log_decision(
                regime, agg.buy_score, agg.sell_score, trigger_fired=True,
                ai_action=direction, ai_confidence=confidence,
                ai_sl=sl, ai_tp=tp,
                risk_block_reason=None if order["success"] else "ORDER_REJECTED",
                signals=agg.signals,
            )
```

- [ ] **Step 8: Run full test suite to verify no regressions**

```powershell
python -m pytest tests/ --ignore=tests/integration -q
```

Expected: 135 passed (all existing tests pass; `signals=None` implicit in existing test calls)

- [ ] **Step 9: Commit**

```powershell
git add src/schema.sql src/logger/writer.py main.py tests/test_writer.py
git commit -m "feat: add signals JSONB to decisions schema, persist per-strategy breakdown in log_decision"
```

---

## Task 2: Config vars + preflight.py

**Files:**
- Modify: `src/config.py`
- Modify: `.env.example`
- Create: `preflight.py`

- [ ] **Step 1: Add config vars to `src/config.py`**

Append after the last line of `src/config.py` (currently `MT5_RECONNECT_DELAY_BASE = ...`):

```python

# Dashboard API
DASHBOARD_API_HOST = os.getenv("DASHBOARD_API_HOST", "127.0.0.1")
DASHBOARD_API_PORT = int(os.getenv("DASHBOARD_API_PORT", "8000"))
```

- [ ] **Step 2: Add config vars to `.env.example`**

Append after the `# Phase 4: Production mode` section:

```
# Phase 5: Dashboard API
DASHBOARD_API_HOST=127.0.0.1
DASHBOARD_API_PORT=8000
```

- [ ] **Step 3: Create `preflight.py`**

```python
#!/usr/bin/env python
"""OpenGold preflight check — run before launching main.py."""
import os
import sys
from dotenv import load_dotenv

REQUIRED_VARS = ["MT5_LOGIN", "MT5_PASSWORD", "MT5_SERVER", "DB_PASSWORD"]


def _ok(msg):  print(f"[OK]   {msg}")
def _fail(msg): print(f"[FAIL] {msg}")
def _skip(msg): print(f"[SKIP] {msg}")
def _warn(msg): print(f"[WARN] {msg}")


def check_env() -> bool:
    load_dotenv()
    missing = [k for k in REQUIRED_VARS if not os.getenv(k)]
    if missing:
        for k in missing:
            _fail(f"Missing required env var: {k}")
        return False
    count = sum(1 for _ in open(".env") if "=" in _)  # rough count
    try:
        count = sum(1 for line in open(".env") if "=" in line and not line.strip().startswith("#"))
    except Exception:
        count = "?"
    _ok(f".env loaded ({count} variables)")
    return True


def check_db() -> bool:
    import psycopg2
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "opengold")
    user = os.getenv("DB_USER", "opengold")
    password = os.getenv("DB_PASSWORD")
    try:
        conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
    except Exception as e:
        _fail(f"TimescaleDB: {e} — is docker-compose up?")
        return False
    _ok(f"TimescaleDB connected ({user}@{host}:{port})")
    required_tables = {"candles", "decisions", "trades", "system_state"}
    with conn.cursor() as cur:
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        existing = {row[0] for row in cur.fetchall()}
    conn.close()
    missing_tables = required_tables - existing
    if missing_tables:
        _fail(f"Missing tables: {', '.join(sorted(missing_tables))} — run schema.sql")
        return False
    _ok(f"Tables verified: {', '.join(sorted(required_tables))}")
    return True


def check_mt5() -> bool:
    try:
        import MetaTrader5 as mt5
    except ImportError:
        _fail("MetaTrader5 package not installed")
        return False
    login = int(os.getenv("MT5_LOGIN", "0"))
    password = os.getenv("MT5_PASSWORD", "")
    server = os.getenv("MT5_SERVER", "")
    if not mt5.initialize(login=login, password=password, server=server):
        _fail(f"MT5 initialize failed: {mt5.last_error()} — is MT5 terminal running?")
        return False
    info = mt5.account_info()
    mt5.shutdown()
    if info is None:
        _fail("MT5 connected but account_info() returned None")
        return False
    _ok(f"MT5 connected (account: {info.login}, server: {info.server})")
    return True


def check_dry_run():
    dry_run = os.getenv("DRY_RUN", "false").lower()
    if dry_run == "false":
        _warn("DRY_RUN=false — LIVE MODE, real orders will be placed")
    else:
        _ok("DRY_RUN=true — safe mode, no real orders")


def main():
    print()
    env_ok = check_env()
    if not env_ok:
        _skip("TimescaleDB check skipped (requires .env)")
        _skip("MT5 check skipped (requires .env)")
        check_dry_run()
        print("\n1 or more checks failed. Fix the above before launching.\n")
        sys.exit(1)

    db_ok = check_db()
    if not db_ok:
        _skip("MT5 check skipped (requires DB)")
        check_dry_run()
        print("\n1 check failed. Fix the above before launching.\n")
        sys.exit(1)

    mt5_ok = check_mt5()
    check_dry_run()

    if mt5_ok:
        print("\nAll checks passed. Ready to launch: python main.py\n")
        sys.exit(0)
    else:
        print("\n1 check failed. Fix the above before launching.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Smoke test preflight manually**

```powershell
python preflight.py
```

Expected with MT5 + DB running: `All checks passed. Ready to launch: python main.py`
Expected with DB down: `[FAIL] TimescaleDB: ...`

- [ ] **Step 5: Run existing tests to verify no regressions**

```powershell
python -m pytest tests/ --ignore=tests/integration -q
```

Expected: 135 passed

- [ ] **Step 6: Commit**

```powershell
git add src/config.py .env.example preflight.py
git commit -m "feat: preflight launch validator + DASHBOARD_API config vars"
```

---

## Task 3: FastAPI app skeleton + CORS

**Files:**
- Create: `src/api/__init__.py`
- Create: `src/api/routes/__init__.py`
- Create: `src/api/app.py`

- [ ] **Step 1: Create `src/api/__init__.py`**

Empty file.

- [ ] **Step 2: Create `src/api/routes/__init__.py`**

Empty file.

- [ ] **Step 3: Create `src/api/app.py`**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.mt5_bridge.connection import connect, disconnect
from src.api.routes import candles, account, signals, decisions, trades, stats, status, killswitch


@asynccontextmanager
async def lifespan(app: FastAPI):
    connect()
    yield
    disconnect()


app = FastAPI(title="OpenGold API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(candles.router, prefix="/api")
app.include_router(account.router, prefix="/api")
app.include_router(signals.router, prefix="/api")
app.include_router(decisions.router, prefix="/api")
app.include_router(trades.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(status.router, prefix="/api")
app.include_router(killswitch.router, prefix="/api")
```

(The route files don't exist yet — `app.py` will be updated in later tasks as each route is created.)

Actually, create stub route files first (step 4), then wire them.

- [ ] **Step 4: Create stub files for all 8 routes**

Create each of these with a minimal router:

`src/api/routes/candles.py`:
```python
from fastapi import APIRouter
router = APIRouter()

@router.get("/candles")
def get_candles(limit: int = 200):
    return {"data": []}
```

Repeat the same pattern for `account.py`, `signals.py`, `decisions.py`, `trades.py`, `stats.py`, `status.py`. For `killswitch.py`:
```python
from fastapi import APIRouter
from pydantic import BaseModel
router = APIRouter()

class KillSwitchRequest(BaseModel):
    active: bool

@router.post("/killswitch")
def set_killswitch(body: KillSwitchRequest):
    return {"active": body.active}
```

- [ ] **Step 5: Verify app starts**

```powershell
python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --no-access-log
```

Expected: `Application startup complete.`  
Press Ctrl+C to stop.

- [ ] **Step 6: Commit stubs**

```powershell
git add src/api/
git commit -m "feat: FastAPI app skeleton with CORS and stub routes"
```

---

## Task 4: MT5-backed routes — candles + account

**Files:**
- Modify: `src/api/routes/candles.py`
- Modify: `src/api/routes/account.py`
- Create: `tests/test_api_candles.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_api_candles.py`:

```python
import pandas as pd
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    # Patch lifespan MT5 connect/disconnect so TestClient doesn't need MT5
    with patch("src.api.app.connect"), patch("src.api.app.disconnect"):
        from src.api.app import app
        with TestClient(app) as c:
            yield c


def test_candles_returns_list(client):
    sample = pd.DataFrame({
        "time": [pd.Timestamp("2026-03-25 10:00", tz="UTC")],
        "open": [1920.0], "high": [1921.0], "low": [1919.0],
        "close": [1920.5], "volume": [150.0],
    })
    with patch("src.api.routes.candles.fetch_candles", return_value=sample):
        resp = client.get("/api/candles?limit=1")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["close"] == 1920.5


def test_candles_mt5_disconnected(client):
    with patch("src.api.routes.candles.fetch_candles", return_value=pd.DataFrame()):
        with patch("src.api.routes.candles.is_connected", return_value=False):
            resp = client.get("/api/candles")
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] == "MT5 disconnected"
    assert body["data"] is None


def test_account_returns_balance(client):
    with patch("src.api.routes.account.get_account_info", return_value={"balance": 10000.0, "equity": 10042.0, "currency": "USD"}):
        with patch("src.api.routes.account.get_positions", return_value=[]):
            resp = client.get("/api/account")
    assert resp.status_code == 200
    body = resp.json()
    assert body["balance"] == 10000.0
    assert body["positions"] == []


def test_account_mt5_disconnected(client):
    with patch("src.api.routes.account.get_account_info", return_value={}):
        with patch("src.api.routes.account.is_connected", return_value=False):
            resp = client.get("/api/account")
    assert resp.status_code == 200
    assert resp.json()["error"] == "MT5 disconnected"
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/test_api_candles.py -v
```

Expected: FAIL (stub routes return empty/wrong data)

- [ ] **Step 3: Implement `src/api/routes/candles.py`**

```python
from fastapi import APIRouter
from src.mt5_bridge.data import fetch_candles
from src.mt5_bridge.connection import is_connected

router = APIRouter()


@router.get("/candles")
def get_candles(limit: int = 200):
    df = fetch_candles(limit)
    if df.empty and not is_connected():
        return {"error": "MT5 disconnected", "data": None}
    records = []
    for _, row in df.iterrows():
        records.append({
            "time": int(row["time"].timestamp()),
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume": row["volume"],
        })
    return {"data": records}
```

- [ ] **Step 4: Implement `src/api/routes/account.py`**

```python
from fastapi import APIRouter
from src.mt5_bridge.connection import get_account_info, is_connected
from src.mt5_bridge.data import get_positions

router = APIRouter()


@router.get("/account")
def get_account():
    if not is_connected():
        return {"error": "MT5 disconnected", "data": None}
    info = get_account_info()
    positions = get_positions()
    return {
        "balance": info.get("balance"),
        "equity": info.get("equity"),
        "currency": info.get("currency"),
        "positions": positions,
    }
```

- [ ] **Step 5: Run tests to verify they pass**

```powershell
python -m pytest tests/test_api_candles.py -v
```

Expected: 4 passed

- [ ] **Step 6: Run full suite**

```powershell
python -m pytest tests/ --ignore=tests/integration -q
```

Expected: 139 passed (135 existing + 4 new)

- [ ] **Step 7: Commit**

```powershell
git add src/api/routes/candles.py src/api/routes/account.py tests/test_api_candles.py
git commit -m "feat: /api/candles and /api/account routes with MT5 bridge"
```

---

## Task 5: DB-backed routes — signals, decisions, trades

**Files:**
- Modify: `src/api/routes/signals.py`
- Modify: `src/api/routes/decisions.py`
- Modify: `src/api/routes/trades.py`
- Create: `tests/test_api_signals.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_api_signals.py`:

```python
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with patch("src.api.app.connect"), patch("src.api.app.disconnect"):
        from src.api.app import app
        with TestClient(app) as c:
            yield c


def test_signals_empty_decisions_table(client):
    with patch("src.api.routes.signals.execute", return_value=[]):
        with patch("src.api.routes.signals.is_connected", return_value=True):
            resp = client.get("/api/signals")
    assert resp.status_code == 200
    body = resp.json()
    assert body["signals"] is None
    assert body["message"] == "No data yet"
    assert body["connected"] is True


def test_signals_returns_latest_row(client):
    import json
    signals_dict = {"ma_crossover": {"signal": "BUY", "confidence": 0.85}}
    row = ("TRENDING", 7.5, 1.2, json.dumps(signals_dict))
    with patch("src.api.routes.signals.execute", return_value=[row]):
        with patch("src.api.routes.signals.is_connected", return_value=True):
            resp = client.get("/api/signals")
    assert resp.status_code == 200
    body = resp.json()
    assert body["regime"] == "TRENDING"
    assert body["buy_score"] == 7.5
    assert body["signals"]["ma_crossover"]["signal"] == "BUY"


def test_decisions_returns_list(client):
    from datetime import datetime, timezone
    row = (datetime(2026, 3, 25, 10, 0, tzinfo=timezone.utc), "TRENDING", 7.5, 1.2, True, "BUY", 0.85, 1900.0, 1950.0, None)
    with patch("src.api.routes.decisions.execute", return_value=[row]):
        resp = client.get("/api/decisions?limit=1")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["regime"] == "TRENDING"


def test_trades_returns_list(client):
    from datetime import datetime, timezone
    dt = datetime(2026, 3, 25, 10, 0, tzinfo=timezone.utc)
    row = (dt, dt, "BUY", 0.01, 1920.0, 1940.0, 1910.0, 1950.0, 42.0, "WIN")
    with patch("src.api.routes.trades.execute", return_value=[row]):
        resp = client.get("/api/trades?limit=1")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["result"] == "WIN"
    assert data[0]["pnl"] == 42.0
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/test_api_signals.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement `src/api/routes/signals.py`**

```python
import json
from fastapi import APIRouter
from src.db import execute
from src.mt5_bridge.connection import is_connected

router = APIRouter()


@router.get("/signals")
def get_signals():
    connected = is_connected()
    try:
        rows = execute(
            "SELECT regime, buy_score, sell_score, signals FROM decisions ORDER BY time DESC LIMIT 1",
            fetch=True,
        )
    except Exception:
        return {"error": "Database unavailable"}, 503
    if not rows:
        return {"signals": None, "regime": None, "buy_score": None, "sell_score": None,
                "connected": connected, "message": "No data yet"}
    regime, buy_score, sell_score, signals_raw = rows[0]
    signals = json.loads(signals_raw) if signals_raw else None
    return {"regime": regime, "buy_score": buy_score, "sell_score": sell_score,
            "signals": signals, "connected": connected}
```

- [ ] **Step 4: Implement `src/api/routes/decisions.py`**

```python
from fastapi import APIRouter
from src.db import execute

router = APIRouter()


@router.get("/decisions")
def get_decisions(limit: int = 50):
    try:
        rows = execute(
            """SELECT time, regime, buy_score, sell_score, trigger_fired,
                      ai_action, ai_confidence, ai_sl, ai_tp, risk_block_reason
               FROM decisions ORDER BY time DESC LIMIT %s""",
            (limit,), fetch=True,
        )
    except Exception:
        return {"error": "Database unavailable"}, 503
    data = [
        {"time": str(r[0]), "regime": r[1], "buy_score": r[2], "sell_score": r[3],
         "trigger_fired": r[4], "ai_action": r[5], "ai_confidence": r[6],
         "ai_sl": r[7], "ai_tp": r[8], "risk_block_reason": r[9]}
        for r in (rows or [])
    ]
    return {"data": data}
```

- [ ] **Step 5: Implement `src/api/routes/trades.py`**

```python
from fastapi import APIRouter
from src.db import execute

router = APIRouter()


@router.get("/trades")
def get_trades(limit: int = 50):
    try:
        rows = execute(
            """SELECT open_time, close_time, direction, lot_size,
                      open_price, close_price, sl, tp, pnl, result
               FROM trades ORDER BY close_time DESC LIMIT %s""",
            (limit,), fetch=True,
        )
    except Exception:
        return {"error": "Database unavailable"}, 503
    data = [
        {"open_time": str(r[0]), "close_time": str(r[1]), "direction": r[2],
         "lot_size": r[3], "open_price": r[4], "close_price": r[5],
         "sl": r[6], "tp": r[7], "pnl": r[8], "result": r[9]}
        for r in (rows or [])
    ]
    return {"data": data}
```

- [ ] **Step 6: Run tests to verify they pass**

```powershell
python -m pytest tests/test_api_signals.py -v
```

Expected: 4 passed

- [ ] **Step 7: Run full suite**

```powershell
python -m pytest tests/ --ignore=tests/integration -q
```

Expected: 143 passed

- [ ] **Step 8: Commit**

```powershell
git add src/api/routes/signals.py src/api/routes/decisions.py src/api/routes/trades.py tests/test_api_signals.py
git commit -m "feat: /api/signals, /api/decisions, /api/trades routes"
```

---

## Task 6: stats + status + killswitch routes

**Files:**
- Modify: `src/api/routes/stats.py`
- Modify: `src/api/routes/status.py`
- Modify: `src/api/routes/killswitch.py`
- Create: `tests/test_api_stats.py`
- Create: `tests/test_api_status.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_api_stats.py`:

```python
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone


@pytest.fixture
def client():
    with patch("src.api.app.connect"), patch("src.api.app.disconnect"):
        from src.api.app import app
        with TestClient(app) as c:
            yield c


def test_stats_empty_trades(client):
    with patch("src.api.routes.stats.execute", return_value=[]):
        resp = client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["win_rate"] is None
    assert body["total_pnl"] == 0.0
    assert body["pnl_curve"] == []


def test_stats_computes_correctly(client):
    dt1 = datetime(2026, 3, 25, 10, 0, tzinfo=timezone.utc)
    dt2 = datetime(2026, 3, 25, 11, 0, tzinfo=timezone.utc)
    # (close_time, pnl, result)
    rows = [(dt1, 42.0, "WIN"), (dt2, -18.0, "LOSS")]
    with patch("src.api.routes.stats.execute", return_value=rows):
        resp = client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["win_rate"] == 0.5
    assert body["total_pnl"] == 24.0
    assert body["avg_win"] == 42.0
    assert body["avg_loss"] == -18.0
    assert len(body["pnl_curve"]) == 2
    assert body["pnl_curve"][0]["time"] == int(dt1.timestamp())
    assert body["pnl_curve"][0]["value"] == 42.0
    assert body["pnl_curve"][1]["value"] == 24.0  # cumulative
```

Create `tests/test_api_status.py`:

```python
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta


@pytest.fixture
def client():
    with patch("src.api.app.connect"), patch("src.api.app.disconnect"):
        from src.api.app import app
        with TestClient(app) as c:
            yield c


def test_status_bot_alive(client):
    recent = datetime.now(timezone.utc) - timedelta(seconds=10)
    with patch("src.api.routes.status.execute", return_value=[(recent,)]):
        with patch("src.api.routes.status.get_kill_switch_state", return_value=False):
            resp = client.get("/api/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["bot_alive"] is True
    assert body["kill_switch_active"] is False


def test_status_bot_offline(client):
    stale = datetime.now(timezone.utc) - timedelta(seconds=120)
    with patch("src.api.routes.status.execute", return_value=[(stale,)]):
        with patch("src.api.routes.status.get_kill_switch_state", return_value=False):
            resp = client.get("/api/status")
    body = resp.json()
    assert body["bot_alive"] is False


def test_killswitch_post(client):
    with patch("src.api.routes.killswitch.set_kill_switch") as mock_ks:
        resp = client.post("/api/killswitch", json={"active": True})
    assert resp.status_code == 200
    mock_ks.assert_called_once_with(True)
    assert resp.json()["active"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/test_api_stats.py tests/test_api_status.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement `src/api/routes/stats.py`**

```python
from fastapi import APIRouter
from src.db import execute

router = APIRouter()


@router.get("/stats")
def get_stats():
    try:
        rows = execute(
            "SELECT close_time, pnl, result FROM trades ORDER BY close_time ASC",
            fetch=True,
        )
    except Exception:
        return {"error": "Database unavailable"}, 503

    if not rows:
        return {"win_rate": None, "total_pnl": 0.0, "avg_win": None, "avg_loss": None, "pnl_curve": []}

    wins = [r[1] for r in rows if r[2] == "WIN"]
    losses = [r[1] for r in rows if r[2] == "LOSS"]
    total = len(rows)
    win_rate = len(wins) / total if total else None
    total_pnl = sum(r[1] for r in rows)
    avg_win = sum(wins) / len(wins) if wins else None
    avg_loss = sum(losses) / len(losses) if losses else None

    cumulative = 0.0
    pnl_curve = []
    for close_time, pnl, _ in rows:
        cumulative += pnl
        pnl_curve.append({"time": int(close_time.timestamp()), "value": round(cumulative, 2)})

    return {
        "win_rate": round(win_rate, 4) if win_rate is not None else None,
        "total_pnl": round(total_pnl, 2),
        "avg_win": round(avg_win, 2) if avg_win is not None else None,
        "avg_loss": round(avg_loss, 2) if avg_loss is not None else None,
        "pnl_curve": pnl_curve,
    }
```

- [ ] **Step 4: Implement `src/api/routes/status.py`**

```python
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
        rows = execute("SELECT time FROM decisions ORDER BY time DESC LIMIT 1", fetch=True)
    except Exception:
        return {"error": "Database unavailable"}, 503

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
```

- [ ] **Step 5: Implement `src/api/routes/killswitch.py`**

```python
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
```

- [ ] **Step 6: Run tests to verify they pass**

```powershell
python -m pytest tests/test_api_stats.py tests/test_api_status.py -v
```

Expected: 5 passed

- [ ] **Step 7: Run full suite**

```powershell
python -m pytest tests/ --ignore=tests/integration -q
```

Expected: 148 passed (135 + 13 new)

- [ ] **Step 8: Commit**

```powershell
git add src/api/routes/stats.py src/api/routes/status.py src/api/routes/killswitch.py tests/test_api_stats.py tests/test_api_status.py
git commit -m "feat: /api/stats, /api/status, /api/killswitch routes + tests"
```

---

## Task 7: End-to-end smoke test + final verification

- [ ] **Step 1: Verify API server starts and responds**

```powershell
# In terminal 1:
uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --no-access-log
```

```powershell
# In terminal 2 (with MT5 + DB running):
Invoke-WebRequest -Uri http://127.0.0.1:8000/api/status | Select-Object -ExpandProperty Content
```

Expected: JSON with `bot_alive`, `dry_run`, `kill_switch_active` keys.

- [ ] **Step 2: Run complete test suite**

```powershell
python -m pytest tests/ --ignore=tests/integration -q
```

Expected: ≥148 passed, 0 failed

- [ ] **Step 3: Final commit + tag**

```powershell
git add .
git commit -m "feat: Phase 5 backend complete - preflight, schema, API (8 endpoints), 13+ new tests"
git tag v0.4.0-backend
```
