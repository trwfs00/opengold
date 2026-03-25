# OpenGold Phase 5: Preflight Script + Web Dashboard

**Date:** 2026-03-25  
**Status:** Approved for implementation  
**Scope:** Two features — (1) a preflight launch validator and (2) a local-only web dashboard for monitoring and control  

---

## Overview

Phase 5 adds operational tooling to OpenGold:

1. **`preflight.py`** — a standalone Python script that validates all dependencies (`.env`, TimescaleDB, MT5 terminal) before launching the bot, reporting pass/fail with clear guidance.
2. **Web Dashboard** — a local-only dashboard (`http://localhost:3000`) built with Next.js (frontend) + FastAPI (API backend), giving full visibility into the bot's state: live price chart, strategy signals, account info, decision log, trade journal, and performance stats. Includes a kill switch toggle.

The existing `main.py` bot, all of `src/`, and all existing tests are unchanged. Both features are additive.

---

## Architecture

### High-level topology

```
[MT5 Terminal (Windows)]
        |
   mt5_bridge (Python)
        |
[main.py bot loop] → [TimescaleDB (Docker)]
                                |
                         [src/api/ FastAPI]  ← binds 127.0.0.1:8000
                                |
                       [dashboard/ Next.js]  ← binds localhost:3000
                          (polls every 5s)
```

Three processes run concurrently on the local machine:
1. `python main.py` — the trading bot (existing)
2. `uvicorn src.api.app:app --host 127.0.0.1 --port 8000` — FastAPI JSON API
3. `cd dashboard && npm run dev` (or `npm start`) — Next.js dashboard

### Repository structure additions

```
opengold/
├── preflight.py              ← NEW: launch validator
├── src/
│   └── api/                  ← NEW: FastAPI backend
│       ├── __init__.py
│       ├── app.py            ← FastAPI instance, CORS, router mounts
│       └── routes/
│           ├── candles.py
│           ├── account.py
│           ├── signals.py
│           ├── decisions.py
│           ├── trades.py
│           ├── stats.py
│           ├── status.py
│           └── killswitch.py
├── dashboard/                ← NEW: Next.js frontend
│   ├── app/
│   │   └── page.tsx
│   ├── components/
│   │   ├── StatusBar.tsx
│   │   ├── AccountPanel.tsx
│   │   ├── CandleChart.tsx
│   │   ├── SignalsPanel.tsx
│   │   ├── DecisionsTable.tsx
│   │   ├── TradesTable.tsx
│   │   └── StatsPanel.tsx
│   ├── lib/
│   │   └── api.ts
│   └── package.json
├── tests/
│   └── test_api_*.py         ← NEW: ~15 FastAPI route tests
```

---

## Feature 1: Preflight Script (`preflight.py`)

### Purpose

Run once before launching the bot. Validates that all required services and configuration are healthy. Exits 0 if all pass, exits 1 if any fail.

### Checks (in order)

1. **`.env` exists and required vars are set**  
   Required vars: `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`, `DB_PASSWORD`.  
   `preflight.py` loads `.env` directly via `python-dotenv` (`load_dotenv()` + `os.getenv()`). It does **NOT** import `src.config` for this check — `src/config.py` uses bare `os.environ["KEY"]` access which raises `KeyError` before any formatted output can be printed if vars are absent. Reports each missing key individually.

2. **TimescaleDB reachable**  
   Uses `psycopg2.connect()` with the credentials from `.env` (direct `os.getenv()` calls).  
   Verifies these tables exist: `candles`, `decisions`, `trades`, `system_state`.

3. **MT5 terminal running and connectable**  
   Calls `mt5.initialize()` + `mt5.account_info()` then `mt5.shutdown()`.  
   Reports account name and server on success.

4. **DRY_RUN mode warning**  
   Always reports current `DRY_RUN` value (read via `os.getenv("DRY_RUN", "false")`).  
   Prints a prominent warning if `DRY_RUN=false` (live trading mode).

Checks 2, 3, and 4 are skipped (with `[SKIP]`) if check 1 fails. Check 3 is skipped if check 2 fails. Check 4 (DRY_RUN) runs independently — it reads only `os.getenv("DRY_RUN", "false")` with no DB dependency, so it runs even when the DB is down. This ensures a live-mode warning is never suppressed by a DB failure.

### Output format

Success:
```
[OK]  .env loaded (48 variables)
[OK]  TimescaleDB connected (opengold@localhost:5432)
[OK]  Tables verified: candles, decisions, trades, system_state
[OK]  MT5 connected (account: 5048406324, server: MetaQuotes-Demo)
[WARN] DRY_RUN=false — LIVE MODE, real orders will be placed

All checks passed. Ready to launch: python main.py
```

Failure:
```
[OK]  .env loaded
[FAIL] TimescaleDB: connection refused (localhost:5432) — is docker-compose up?
[SKIP] MT5 check skipped (requires DB)
[SKIP] DRY_RUN check skipped

1 check failed. Fix the above before launching.
```

### Implementation notes

- No new dependencies — uses existing `psycopg2`, `MetaTrader5`, `python-dotenv`
- Does **not** import `src.config` — reads `.env` directly to avoid `KeyError` on missing vars
- Does not start or modify any services
- Single file, standalone

---

## Schema change: `decisions` table

The `signals` per-strategy breakdown (computed by `aggregator/scorer.py` as `AggregateResult.signals`) is currently held in memory only. To back the `SignalsPanel`, it must be persisted.

**Change to `src/schema.sql`:** Update the `CREATE TABLE decisions` definition to include the new column, and add a migration comment for existing deployments:
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
```

**Stored format:**
```json
{
  "ma_crossover": {"signal": "BUY", "confidence": 0.85},
  "macd":         {"signal": "BUY", "confidence": 0.72},
  "rsi":          {"signal": "NEUTRAL", "confidence": 0.50},
  ...
}
```

**Change to `src/logger/writer.py`:** `log_decision()` gains an optional `signals` parameter:
```python
def log_decision(
    ...,
    signals: dict | None = None,   # AggregateResult.signals
):
```
Before inserting, serialize the dict with `json.dumps(signals)` (or pass `None`). `psycopg2` cannot adapt a raw Python `dict` to `JSONB` directly — `json.dumps()` produces a string which is accepted by the `JSONB` column.

**Change to `main.py`:** Pass `agg.signals` at **all 4** `log_decision()` call sites:
1. Trigger not fired (line ~130): `log_decision(regime, ..., trigger_fired=False, signals=agg.signals)`
2. AI returned SKIP (line ~145): `log_decision(regime, ..., ai_action="SKIP", signals=agg.signals)`
3. Risk blocked (line ~170): `log_decision(regime, ..., risk_block_reason=risk.block_reason, signals=agg.signals)`
4. Order placed/rejected (line ~179): `log_decision(regime, ..., signals=agg.signals)`

Existing calls in `tests/test_main.py` pass `signals=None` implicitly — no test breakage.

---

## Feature 2: FastAPI API (`src/api/`)

### Purpose

Read-only JSON API exposing bot state to the dashboard. Runs as a separate process from `main.py`. Binds exclusively to `127.0.0.1` (localhost only, no external access). The only write operation is the kill switch toggle.

### Configuration

New environment variables (added to `.env.example` and `src/config.py`):
```
DASHBOARD_API_PORT=8000
DASHBOARD_API_HOST=127.0.0.1
```

### CORS

Allowed origins: `http://localhost:3000`, `http://localhost:3001`

### Endpoints

| Method | Path | Data source | Description |
|--------|------|-------------|-------------|
| `GET` | `/api/candles?limit=200` | MT5 bridge (`fetch_candles()`) | Last N M1 OHLCV candles for price chart |
| `GET` | `/api/account` | MT5 bridge (`get_account_info()`, `get_positions()`) | Balance, equity, currency, open positions |
| `GET` | `/api/signals` | TimescaleDB decisions (latest row, including `signals` JSONB) + `is_connected()` | Regime, buy/sell scores, individual strategy signals |
| `GET` | `/api/decisions?limit=50` | TimescaleDB `decisions` table | Recent decision log |
| `GET` | `/api/trades?limit=50` | TimescaleDB `trades` table | Recent closed trades |
| `GET` | `/api/stats` | TimescaleDB `trades` table | Win rate, total P&L, avg win, avg loss, P&L curve |
| `GET` | `/api/status` | TimescaleDB `system_state` + config | Bot alive flag, DRY_RUN, kill switch state |
| `POST` | `/api/killswitch` | TimescaleDB `system_state` | Body: `{"active": bool}` — toggle kill switch |

### MT5 connection lifecycle

`app.py` wires MT5 initialization into FastAPI's `lifespan` context manager (the `@app.on_event()` API is deprecated since FastAPI 0.95; `requirements.txt` pins `fastapi>=0.110.0`):
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    connect()    # mt5.initialize()
    yield
    disconnect() # mt5.shutdown()

app = FastAPI(title="OpenGold API", lifespan=lifespan)
```
If `connect()` fails on startup, the API still starts — MT5-backed endpoints return `{"error": "MT5 disconnected", "data": null}` gracefully.

### Bot-alive detection

`/api/status` considers the bot alive if the most recent `decisions` row timestamp is within the last 60 seconds. This is passive — the API never calls `main.py` directly.

### Error responses

If MT5 is disconnected, MT5-backed endpoints return:
```json
{"error": "MT5 disconnected", "data": null}
```

If the DB is unavailable, DB-backed endpoints return HTTP 503:
```json
{"error": "Database unavailable"}
```

If the `decisions` table is empty (bot has not run yet), `/api/signals` returns HTTP 200:
```json
{"signals": null, "regime": null, "buy_score": null, "sell_score": null, "connected": true, "message": "No data yet"}
```
The `SignalsPanel` renders an empty state ("Waiting for first candle…") when `signals` is null.
```json
{"win_rate": null, "total_pnl": 0.0, "avg_win": null, "avg_loss": null, "pnl_curve": []}
```

### File layout

```
src/api/
├── __init__.py
├── app.py          ← FastAPI(title="OpenGold API"), CORSMiddleware, include_routers
└── routes/
    ├── candles.py   ← GET /api/candles
    ├── account.py   ← GET /api/account
    ├── signals.py   ← GET /api/signals
    ├── decisions.py ← GET /api/decisions
    ├── trades.py    ← GET /api/trades
    ├── stats.py     ← GET /api/stats
    ├── status.py    ← GET /api/status
    └── killswitch.py ← POST /api/killswitch
```

### Testing

~15 new tests in `tests/test_api_*.py` using FastAPI `TestClient`. Each route is tested with mocked DB/MT5 dependencies. Specific cases:
- Candles endpoint returns correct shape when MT5 connected
- Candles endpoint returns `{"error": "MT5 disconnected", "data": null}` when disconnected
- Kill switch POST writes to `system_state` table
- Stats endpoint computes correct win rate and cumulative P&L
- Stats endpoint returns zero-row empty state `{"win_rate": null, "total_pnl": 0.0, ...}` when trades table is empty
- Status endpoint reports bot alive/offline correctly
- Signals endpoint returns full 6-key shape `{"signals": null, "regime": null, "buy_score": null, "sell_score": null, "connected": true, "message": "No data yet"}` when decisions table is empty
- DB unavailable → HTTP 503 on decisions/trades/stats/status endpoints

---

## Feature 3: Next.js Dashboard (`dashboard/`)

### Purpose

Single-page local dashboard at `http://localhost:3000`. Polls all API endpoints every 5 seconds. Dark theme.

### Technology

- **Next.js 14** (App Router, TypeScript)
- **Tailwind CSS** for styling
- **`lightweight-charts`** (TradingView) for candlestick chart and P&L curve

### Page layout

```
┌────────────────────────────────────────────────────────┐
│ StatusBar: ● Bot status | DRY_RUN badge | Kill Switch   │
├─────────────────────────┬──────────────────────────────┤
│ CandleChart             │ AccountPanel                  │
│ XAUUSD M1, 200 candles  │ Balance / Equity              │
│ + trade entry markers   │ Open Positions list           │
├─────────────────────────┴──────────────────────────────┤
│ SignalsPanel                                            │
│ Regime badge | Buy score | Sell score                   │
│ 13 strategy signal badges (BUY/SELL/NEUTRAL)            │
├─────────────────────────┬──────────────────────────────┤
│ DecisionsTable (50 rows)│ TradesTable (50 rows)         │
│ time, regime, scores,   │ time, direction, PnL,         │
│ trigger, AI, block      │ result, regime                │
├─────────────────────────┴──────────────────────────────┤
│ StatsPanel                                              │
│ Win rate | Net P&L | Avg win | Avg loss | P&L curve     │
└────────────────────────────────────────────────────────┘
```

### Component responsibilities

| Component | API endpoints consumed | Key behavior |
|-----------|----------------------|--------------|
| `StatusBar` | `/api/status` | Bot alive dot (green/red), DRY_RUN badge (yellow if active), kill switch toggle button with confirm dialog |
| `AccountPanel` | `/api/account` | Shows balance, equity, and a list of open positions (direction, volume, open price) |
| `CandleChart` | `/api/candles`, `/api/trades` | TradingView Lightweight Charts candlestick series; overlays BUY markers (green arrow up) and SELL markers (red arrow down) from recent trades |
| `SignalsPanel` | `/api/signals` | Regime badge (TRENDING/RANGING/BREAKOUT color-coded); buy/sell aggregate scores; 13 strategy badges (green=BUY, red=SELL, grey=NEUTRAL) |
| `DecisionsTable` | `/api/decisions` | Scrollable table, most recent first; highlights rows where trigger fired |
| `TradesTable` | `/api/trades` | Scrollable table; WIN rows green, LOSS rows red |
| `StatsPanel` | `/api/stats` | Summary cards + Lightweight Charts linear P&L chart |

### Polling

```typescript
// lib/api.ts
const POLL_INTERVAL = 5000  // matches bot's POLL_INTERVAL_SECONDS default

// In page.tsx:
useEffect(() => {
  const tick = () => Promise.all([fetchAll endpoints])
  tick()
  const id = setInterval(tick, POLL_INTERVAL)
  return () => clearInterval(id)
}, [])
```

StatusBar displays "Last updated: HH:MM:SS" timestamp.

### Kill switch safety

The kill switch button requires a `window.confirm()` before calling `POST /api/killswitch`. This prevents accidental activation. The bot picks up the state change on its next loop iteration via the existing `get_kill_switch_state()` DB read.

### Error states

Each component handles API errors gracefully:
- Shows an "unavailable" empty state if fetch fails
- Never crashes the page
- StatusBar shows "API offline" if the FastAPI server is not running

---

## Data flow summary

```
Bot loop (every 5s)
  → fetch_candles() → MT5
  → classify_regime(), run_all(), aggregate()
  → log_decision() → TimescaleDB decisions table

Dashboard (every 5s)
  GET /api/candles     → FastAPI → fetch_candles() → MT5
  GET /api/account     → FastAPI → get_account_info() + get_positions() → MT5
  GET /api/signals     → FastAPI → decisions table (latest) + is_connected()
  GET /api/decisions   → FastAPI → decisions table (last 50)
  GET /api/trades      → FastAPI → trades table (last 50)
  GET /api/stats       → FastAPI → trades table (aggregate)
  GET /api/status      → FastAPI → system_state + decisions (recency check)

Kill switch (user action)
  POST /api/killswitch → FastAPI → set_kill_switch() → system_state table
  Bot next loop        → get_kill_switch_state() → reads updated state
```

---

## Out of scope (Phase 5)

- Authentication / password protection (localhost only)
- Alerts (Telegram/email)
- WebSocket real-time push (auto-polling at 5s is sufficient)
- Mobile/responsive design
- Position management (trailing stops)
- Historical backtesting view

---

## Success criteria

- `python preflight.py` exits 0 when MT5 + DB are running; exits 1 with clear error when either is down
- FastAPI starts on port 8000, all 8 endpoints return valid JSON
- Next.js dashboard loads at `http://localhost:3000`, all 7 panels render with live data
- Kill switch toggle from dashboard is reflected in the bot within one loop cycle
- All 135 existing tests continue to pass (plus any new tests for `log_decision` signals parameter)
- ~15 new API tests pass

---

## Dependencies added

**Python (requirements.txt):** No new deps needed (FastAPI + uvicorn already present)

**Node (dashboard/package.json new):**
- `next@14`
- `react`, `react-dom`
- `typescript`
- `tailwindcss`
- `lightweight-charts`
