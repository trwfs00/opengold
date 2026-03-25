# OpenGold — AI-Assisted XAU/USD Trading System Design

**Date:** 2026-03-25  
**Author:** Teerawut Sangkakaro  
**Status:** Approved

---

## 1. Overview

OpenGold is a fully automated 24/7 trading bot for XAU/USD via MetaTrader 5 (Exness demo account). It combines 13 technical strategies with an AI decision layer (Claude Haiku) gated by a cost-optimizing trigger layer. A Trading Journal acts as a guardrail, feeding compact recent trade history into every AI prompt to enable self-correcting behavior. Hard risk limits are enforced synchronously before any order reaches MT5.

### Goals
- Profitable automated trading on XAU/USD
- Minimal Claude API token usage (only call AI when conditions clearly warrant it)
- Adaptive strategy weighting based on market regime
- Hard, non-bypassable risk controls

---

## 2. Architecture — Option B: Modular Python + Docker Data Stack

MT5 Python API runs on Windows host (Windows-only requirement). TimescaleDB runs in Docker via Docker Compose. The Python application is a single process with clearly separated internal modules.

```
mt5_bridge → strategies → aggregator → regime → trigger
                                                    ↓ (only if triggered)
                                              journal (guardrail)
                                                    ↓
                                              ai_layer (Claude Haiku)
                                                    ↓
                                              risk (hard guardrails)
                                                    ↓
                                              executor (MT5 order)
                                                    ↓
                                              logger (TimescaleDB)
```

---

## 3. Project Structure

```
opengold/
├── docker-compose.yml          # TimescaleDB on port 5432
├── .env                        # Secrets — NEVER committed
├── .env.example                # Placeholder template — committed
├── requirements.txt
├── main.py                     # Entry point, main candle loop
├── docs/
│   └── superpowers/specs/      # Design & spec documents
└── src/
    ├── mt5_bridge/             # MT5 connect, fetch candles, place/close orders
    ├── strategies/             # 13 strategy modules
    ├── aggregator/             # Weighted vote combiner
    ├── regime/                 # Market regime classifier
    ├── trigger/                # AI call gate
    ├── ai_layer/               # Claude API wrapper + prompt builder
    ├── journal/                # Recent trade summary for AI context
    ├── risk/                   # Hard guardrail engine
    ├── executor/               # Order placement via MT5
    └── logger/                 # Write all decisions/trades to DB
```

---

## 4. Data Layer

- **Source:** MetaTrader 5 Python API (Windows host)
- **Instrument:** XAU/USD
- **Timeframe:** M1 (1-minute candles)
- **Trigger:** Event-driven on new candle close (Option B — detected by polling last candle timestamp)
- **Storage:** TimescaleDB (PostgreSQL + time-series extension) in Docker

### Database Schema

```sql
-- Time-series price data (TimescaleDB hypertable)
CREATE TABLE candles (
    time        TIMESTAMPTZ NOT NULL,
    open        FLOAT8,
    high        FLOAT8,
    low         FLOAT8,
    close       FLOAT8,
    volume      FLOAT8
);
SELECT create_hypertable('candles', 'time');

-- All decisions (traded or skipped) — also a hypertable for query performance
CREATE TABLE decisions (
    time              TIMESTAMPTZ NOT NULL,
    regime            TEXT,
    buy_score         FLOAT8,
    sell_score        FLOAT8,
    trigger_fired     BOOLEAN,
    ai_action         TEXT,        -- BUY | SELL | SKIP | NULL
    ai_confidence     FLOAT8,
    ai_sl             FLOAT8,
    ai_tp             FLOAT8,
    risk_block_reason TEXT         -- NULL if not blocked
);
SELECT create_hypertable('decisions', 'time');

-- Closed trades (source of truth for journal + performance)
CREATE TABLE trades (
    id          SERIAL PRIMARY KEY,
    open_time   TIMESTAMPTZ,
    close_time  TIMESTAMPTZ,
    direction   TEXT,              -- BUY | SELL
    lot_size    FLOAT8,
    open_price  FLOAT8,
    close_price FLOAT8,
    sl          FLOAT8,
    tp          FLOAT8,
    pnl         FLOAT8,
    result      TEXT               -- WIN | LOSS | BREAKEVEN
    -- BREAKEVEN: |pnl| < 1.00 USD
);

-- Kill switch and daily state (survives restarts)
CREATE TABLE system_state (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TIMESTAMPTZ
);
```

---

## 5. Strategy Engine

### Interface Contract

Every strategy module exposes a single function:

```python
def compute(candles: pd.DataFrame) -> dict:
    # candles: last N rows of OHLCV data
    return {
        "signal": "BUY" | "SELL" | "NEUTRAL",
        "confidence": float  # 0.0 to 1.0
    }
```

### The 13 Strategies

| Category | Strategy |
|---|---|
| Trend Following | MA Crossover, MACD, Ichimoku, Momentum, ADX Trend |
| Mean Reversion | RSI, Bollinger Bands, Stochastic, Mean Reversion |
| Structure/Breakout | Breakout, Support & Resistance |
| Execution | Scalping, VWAP |

### Regime-Weighted Scoring

Strategies are weighted by current market regime before scoring:

| Strategy | TRENDING | RANGING | BREAKOUT |
|---|---|---|---|
| MA Crossover | 1.5 | 0.5 | 0.5 |
| MACD | 1.5 | 0.5 | 0.8 |
| Ichimoku | 1.5 | 0.3 | 0.5 |
| Momentum | 1.2 | 0.3 | 1.0 |
| ADX Trend | 1.5 | 0.3 | 0.8 |
| RSI | 0.3 | 1.5 | 0.5 |
| Bollinger Bands | 0.5 | 1.5 | 1.2 |
| Stochastic | 0.3 | 1.5 | 0.5 |
| Mean Reversion | 0.3 | 1.5 | 0.3 |
| Breakout | 0.5 | 0.5 | 2.0 |
| Support & Resistance | 0.8 | 1.0 | 1.5 |
| Scalping | 0.8 | 1.0 | 1.0 |
| VWAP | 1.0 | 1.0 | 1.0 |

### Aggregator Output

```python
{
  "buy_score": float,   # sum of (weight × confidence) for BUY signals only
  "sell_score": float,  # sum of (weight × confidence) for SELL signals only
  "regime": "TRENDING" | "RANGING" | "BREAKOUT",
  "signals": {
      "ma_crossover": {"signal": "BUY", "confidence": 0.8},
      ...
  }
}
```

**NEUTRAL signal handling:** NEUTRAL signals contribute **zero** to both buy_score and sell_score, regardless of confidence. They are recorded in `signals` for logging but have no effect on scoring.

---

## 6. Market Regime Classifier

Priority order (highest wins when multiple conditions are true): **BREAKOUT > TRENDING > RANGING**

| Priority | Condition | Regime |
|---|---|---|
| 1 (highest) | ATR(current) > 1.5 × ATR_MA(14) | BREAKOUT |
| 2 | ADX(14) > 25 | TRENDING |
| 3 (default) | All others (including ADX ≤ 25 AND BB_width < BB_WIDTH_THRESHOLD) | RANGING |

Configurable parameters (`.env`):
```
ADX_TREND_THRESHOLD=25
ATR_BREAKOUT_MULTIPLIER=1.5
ATR_LOOKBACK=14
BB_WIDTH_THRESHOLD=0.001
BB_LOOKBACK=20
```

---

## 7. Trigger Layer

AI is called **only if ALL conditions are met:**

1. `buy_score >= 5.0` OR `sell_score >= 5.0`
2. `abs(buy_score - sell_score) >= 2.0` (no major directional conflict)
3. Total open trades < `MAX_CONCURRENT_TRADES` (reads from config, default 3)
4. Daily drawdown kill switch is NOT active

Note: The kill switch is also checked in the Risk Engine (§10). This double-check is intentional defense-in-depth — the trigger prevents an unnecessary AI call, and risk provides a final hard block before order placement.

If any condition fails → **SKIP** (zero tokens spent, decision logged with `trigger_fired=False`).

---

## 8. Trading Journal (Guardrail)

Before every AI call, the journal fetches the last N closed trades from the `trades` table (configurable: `JOURNAL_TRADE_COUNT=10`, default 10) and formats them as a compact prefix (~200 tokens).

**Behaviour when fewer than N trades exist:** Use all available trades. If 0 trades exist (fresh system), omit the RECENT TRADES section entirely — the prompt proceeds without journal context.

```
RECENT TRADES (last 10):
[1] BUY  TRENDING  buy=7.1 sell=1.2 → WIN   +$42  (SL=1920.0 TP=1940.0)
[2] BUY  RANGING   buy=5.8 sell=2.1 → LOSS  -$18  (SL=1915.0 TP=1930.0)
[3] SELL BREAKOUT  buy=1.1 sell=6.4 → WIN   +$31  (SL=1935.0 TP=1918.0)
...
Win rate: 7/10 | Avg win: $38 | Avg loss: $21 | Net: +$224
```

This provides AI self-awareness of recent performance without expensive full history context.

---

## 9. AI Decision Layer

### Model Selection
- **Primary:** Claude Haiku (fast, cheap ~$0.001/call)
- **Fallback:** Claude Sonnet (if Haiku returns an error or timeout — one retry only)
- **Never:** Opus (too expensive)
- If both Haiku and Sonnet fail → SKIP candle, log `AI_API_ERROR`

### Prompt Structure

```
[JOURNAL]
<compact trade summary, or omitted if no trades yet>

[MARKET]
Regime: TRENDING | buy_score: 7.2 | sell_score: 1.1
Price: 1923.45 | ATR: 3.2

[TASK]
Decide: BUY, SELL, or SKIP. If BUY or SELL, provide SL and TP in price.
Reply in JSON only: {"action":"BUY","confidence":0.85,"sl":1918.0,"tp":1938.0}
```

Note: `Recent structure` field was removed — no module is assigned to compute market structure. This field may be added in a future phase with a dedicated structure-analysis module.

Total input: ~400–600 tokens per call.

### AI Output Schema

```json
{
  "action": "BUY" | "SELL" | "SKIP",
  "confidence": 0.0–1.0,
  "sl": float,
  "tp": float
}
```

If response is not valid JSON → treat as SKIP, log `AI_PARSE_ERROR`.

---

## 10. Risk Engine (Hard Guardrails)

Runs **synchronously after AI decision, before any MT5 order**. Cannot be bypassed.

### XAU/USD Pip Definition
For XAU/USD on Exness MT5:
- Contract size: 100 troy oz per standard lot
- 1 pip = $0.01 price movement per oz
- Pip value = $0.01 × 100 = **$1.00 per standard lot**
- Lot size formula: `lot = (balance × RISK_PER_TRADE) / (sl_distance_usd × 100)`
  where `sl_distance_usd = abs(entry_price - sl_price)` in USD per oz
- SL sanity expressed in price distance: `$3.00` minimum, `$50.00` maximum
- If computed lot < broker minimum (0.01) → SKIP, log `BELOW_MIN_LOT`

### Kill Switch State
Kill switch state is stored in the `system_state` DB table (survives restarts):
```sql
CREATE TABLE system_state (
    key   TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMPTZ
);
-- key='kill_switch_active', value='true'/'false'
-- key='kill_switch_date', value='2026-03-25' (UTC date it was triggered)
```
On each candle, before processing: read kill switch from DB. If `kill_switch_date` < today UTC → auto-reset to inactive.

### Daily Drawdown Baseline
The 5% drawdown is measured against **account balance at UTC midnight** (stored in `system_state` as `key='daily_start_balance'`, refreshed at each UTC midnight).

| Check | Rule | On Failure |
|---|---|---|
| Daily drawdown kill switch | Current equity < `daily_start_balance × (1 - DAILY_DRAWDOWN_LIMIT)` | Set kill switch in DB; block all trades until next UTC day |
| Max concurrent trades | Total open trades ≥ `MAX_CONCURRENT_TRADES` | SKIP, log `MAX_TRADES_REACHED` |
| Lot sizing | `lot = (balance × RISK_PER_TRADE) / (sl_distance_usd × 100)` | Adjust down; if below 0.01 → SKIP, log `BELOW_MIN_LOT` |
| Min AI confidence | confidence < `MIN_AI_CONFIDENCE` | SKIP, log `LOW_CONFIDENCE` |
| SL sanity | SL price distance < `MIN_SL_USD` OR > `MAX_SL_USD` | SKIP, log `INVALID_SL` |

Risk parameters (configurable via `.env`):
```
RISK_PER_TRADE=0.01           # 1% of balance per trade
MAX_CONCURRENT_TRADES=3
DAILY_DRAWDOWN_LIMIT=0.05     # 5% of daily start balance
MIN_AI_CONFIDENCE=0.65
MIN_SL_USD=3.00               # Minimum SL distance in USD per oz
MAX_SL_USD=50.00              # Maximum SL distance in USD per oz
```

---

## 11. Execution Layer

- Place order via `mt5.order_send()` with SL and TP from AI (after risk adjustment)
- Track open positions by polling `mt5.positions_get()` on each candle
- Detect closed trades by comparing position snapshots → write to `trades` table
- No manual SL/TP moving — set once at open, let MT5 manage

### Missed Trade Reconciliation
On every MT5 reconnection after a disconnect: query `mt5.history_deals_get(from_date, to_date)` to retrieve any deals closed during the outage and write them to the `trades` table (skip duplicates by checking existing `open_time + direction + open_price`). This ensures journal and drawdown calculations remain accurate after restarts or disconnects.

---

## 12. Error Handling

| Failure | Behavior |
|---|---|
| MT5 connection lost | Retry 3× with exponential backoff (2s, 4s, 8s), then pause loop; run reconciliation on reconnect |
| Claude Haiku error/timeout | Retry once with Claude Sonnet; if Sonnet also fails → SKIP, log `AI_API_ERROR` |
| Claude returns malformed JSON | SKIP, log `AI_PARSE_ERROR`, do not retry |
| DB connection lost | Buffer up to 1000 records in memory; retry every 30s for up to 1 hour; if >1 hour → log critical alert and continue without writing |
| MT5 order rejected | Log `ORDER_REJECTED` with reason, do not retry same signal |
| Daily kill switch active | Log `KILL_SWITCH_ACTIVE`, skip all signals until next UTC day; state persists in DB across restarts |

Bot never crashes on external failures — degrades gracefully.

Configurable via `.env`:
```
POLL_INTERVAL_SECONDS=5      # Candle detection polling frequency
DB_BUFFER_MAX_RECORDS=1000
DB_RETRY_INTERVAL_SECONDS=30
DB_MAX_RETRY_DURATION_SECONDS=3600
```

---

## 13. Tech Stack

| Component | Technology |
|---|---|
| Core bot | Python 3.11+ |
| MT5 API | `MetaTrader5` Python package (Windows only) |
| AI | Anthropic Claude API (`anthropic` Python SDK) |
| Database | TimescaleDB (PostgreSQL + timescaledb extension) |
| DB client | `psycopg2` |
| Data processing | `pandas`, `numpy`, `pandas-ta` |
| Infrastructure | Docker Desktop + Docker Compose |
| Secrets | `.env` file (never committed) |
| Dashboard backend | FastAPI + uvicorn |
| Dashboard frontend | Plain HTML/JS (no build step) |

---

## 14. Security

- `.env` is in `.gitignore` from project initialization
- `.env.example` with placeholder values is committed instead
- MT5 credentials and Claude API key are never hardcoded
- No web-facing surface — bot runs locally on Windows

---

## 15. Development Phases

| Phase | Scope |
|---|---|
| 1 — Core | MT5 bridge, all 13 strategies, execution, basic logging |
| 2 — Aggregation | Signal aggregator, regime classifier, trigger layer |
| 3 — AI Integration | Claude Haiku integration, journal guardrail, risk engine |
| 4 — Dashboard | Web monitoring UI (see §16) |
| 5 — Optimization | Tune trigger thresholds, strategy weights, prompt compression |
| 6 — OpenClaw (future) | Multi-step agent with tool use |

**Gate to live trading:** All unit tests pass + 1 week demo run with zero crashes.

---

## 16. Dashboard (Phase 4)

A local web UI for monitoring bot activity in real time. Inspired by a dark terminal aesthetic (green-on-black, trading-terminal style). Reads from TimescaleDB — the bot itself requires no changes.

### Tech Stack
- **Backend:** FastAPI (Python) — REST + WebSocket endpoints, reads TimescaleDB
- **Frontend:** Single-page app (plain HTML/JS or lightweight framework) — no build step required
- **Served locally:** `http://localhost:8080` — not exposed to the internet
- **Added to `docker-compose.yml`** alongside TimescaleDB

### Panels (from top to bottom)

| Panel | Content |
|---|---|
| Header bar | Instrument (XAU/USD), live price, P&L today, win/loss count, live indicator |
| Price chart | Line chart of last N candles, auto-refreshes every candle |
| Performance stats | Win rate %, total trades, avg win/loss ratio, consecutive wins/losses |
| Current signal | Regime badge, buy_score, sell_score, directional bias bar |
| Trade Journal | Last 10 closed trades — direction, entry/exit, PnL, result badge, AI reasoning text |
| Strategy signals | Bar per strategy showing signal strength (BUY/SELL/NEUTRAL + confidence) |
| Under the Hood | Latest AI prompt summary, AI decision, confidence, risk block reason (if any) |
| Kill switch indicator | Red banner when daily drawdown kill switch is active |

### API Endpoints (FastAPI)

```
GET  /api/status          Current regime, scores, open positions, kill switch state
GET  /api/trades?limit=10  Last N closed trades
GET  /api/decisions?limit=50 Last N decision log entries
GET  /api/candles?limit=100  Last N candles for chart
WS   /ws/live              WebSocket — pushes new candle/decision events in real time
```

### Security
- Dashboard is local-only (`127.0.0.1` bind, not `0.0.0.0`)
- No authentication required for local use
- DB credentials are not exposed to the frontend (backend handles all DB queries)

---

## 16. Future Improvements

- Reinforcement learning for strategy weight tuning
- Per-strategy performance tracking and auto-disable
- Portfolio-level optimization (multi-symbol)
- OpenClaw agent with tool-based execution
