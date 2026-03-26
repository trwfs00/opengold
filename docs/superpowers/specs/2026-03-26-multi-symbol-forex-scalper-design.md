# Design: Multi-Symbol Bot — Forex Scalper (EURUSD) Extension

**Date:** 2026-03-26  
**Status:** Revised (post-review)  
**Author:** Brainstorming session

---

## 1. Goal

Extend the existing opengold trading bot to support a second trading mode — a Forex scalper targeting EURUSD on M5 timeframe — while keeping the Gold bot (XAUUSD) running unmodified.

**Phase targets:**
- Phase 1: 100–300 THB/day, consistency focus
- Phase 2: compound via increased lot as profit grows
- Phase 3: 300–1,000 THB/day naturally

---

## 2. Decisions Made

| Question | Decision |
|----------|----------|
| Mode switching | Dual process (D) — Gold and Forex run as separate processes |
| Dashboard | Tab switch (B) — single port 3000, tab toggles between bots |
| Database | Separate DB (B) — `opengold` (Gold) and `openforex` (Forex) |

---

## 3. Architecture

### 3.1 Approach: Multi-instance with ENV profiles

Single shared codebase. Each bot instance loads a different `.env` file via `--env` CLI flag, which sets `BOT_ID`, `SYMBOL`, port, DB, and risk parameters.

```
opengold/
├── main.py                  # shared entrypoint, reads --env flag
├── gold.env                 # Gold bot config (renamed from .env)
├── forex.env                # Forex Scalper config (new)
├── src/
│   ├── config.py            # +SYMBOL, CONTRACT_SIZE, PIP_VALUE_PER_LOT, BOT_ID, API_PORT, MAX_TRADES_PER_DAY
│   ├── mt5_bridge/data.py   # SYMBOL/TIMEFRAME from config (not hardcoded)
│   ├── risk/engine.py       # lot formula branches on CONTRACT_SIZE
│   └── ai_layer/prompt.py   # dynamic asset/instrument context
└── dashboard/
    ├── next.config.ts        # GOLD_API_URL=:8000, FOREX_API_URL=:8001
    ├── lib/api.ts            # fetchStatus(bot: "gold"|"forex") → selects API URL
    └── components/
        └── BotTabSwitcher    # "GOLD" | "FOREX" tab in StatusBar area
```

### 3.2 Runtime

```bash
# Terminal 1 — Gold bot (port 8000, DB: opengold)
python main.py --env gold.env

# Terminal 2 — Forex Scalper (port 8001, DB: openforex)
python main.py --env forex.env
```

---

## 4. Forex Scalper Config (`forex.env`)

```ini
BOT_ID=forex
SYMBOL=EURUSD
TIMEFRAME=M5
CONTRACT_SIZE=100000          # Forex standard lot = 100,000 units
PIP_VALUE_PER_LOT=10          # $10 per pip per standard lot
SL_PIPS_MIN=3
SL_PIPS_MAX=5
TP_PIPS_MIN=4                  # must satisfy MIN_RR_RATIO: ceil(SL_PIPS_MIN * MIN_RR_RATIO) = ceil(3 * 1.3) = 4
TP_PIPS_MAX=5
MIN_RR_RATIO=1.3              # TP 3–5 pip vs SL 3–5 pip
RISK_PER_TRADE=0.01           # 1% balance per trade
MIN_AI_CONFIDENCE=0.75        # strict LLM filter
TRIGGER_MIN_SCORE=4.0
TRIGGER_MIN_SCORE_DIFF=1.5
AI_INTERVAL_MINUTES=1         # M5 candles → fire more often
TRADE_SESSIONS_UTC=7-17       # London 07:00–16:59 UTC (end is exclusive: hour < end). Use 17 to include 16:xx candle.
MAX_TRADES_PER_DAY=15
DAILY_DRAWDOWN_LIMIT=0.03     # stop trading at -3% per day
DB_NAME=openforex
DB_USER=opengold
DB_PASSWORD=<same>
API_PORT=8001
```

---

## 5. Code Changes Required

### 5.1 `src/config.py`
Add new fields:
```python
BOT_ID = os.getenv("BOT_ID", "gold")
SYMBOL = os.getenv("SYMBOL", "XAUUSD")
TIMEFRAME = os.getenv("TIMEFRAME", "M1")
CONTRACT_SIZE = float(os.getenv("CONTRACT_SIZE", "100"))       # Gold=100 oz, Forex=100000
PIP_VALUE_PER_LOT = float(os.getenv("PIP_VALUE_PER_LOT", "10"))
SL_PIPS_MIN = float(os.getenv("SL_PIPS_MIN", "3"))
SL_PIPS_MAX = float(os.getenv("SL_PIPS_MAX", "50"))
MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", "999"))
# Override existing:
DASHBOARD_API_PORT = int(os.getenv("API_PORT", "8000"))
```

Also: `main.py` must be restructured into two phases:

```python
# PHASE 1: parse --env flag and load dotenv BEFORE any src.* imports
import argparse
from dotenv import load_dotenv

parser = argparse.ArgumentParser()
parser.add_argument("--env", default=".env")
args, _ = parser.parse_known_args()
load_dotenv(args.env, override=True)  # override=True so env file wins over OS env vars

# PHASE 2: only now import src modules (config reads from already-loaded env)
from src import config
from src.mt5_bridge import data
# ... rest of imports
```

**Critical:** Every `from src import ...` at the top of `main.py` must be moved below the `load_dotenv()` call. Python evaluates module-level imports before `__main__` block runs — without this restructure, config is frozen to OS env values at import time and `--env` flag has no effect.

### 5.2 `src/mt5_bridge/data.py`
```python
# Remove hardcoded:
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M1

# Replace with:
from src import config
SYMBOL = config.SYMBOL
TIMEFRAME = getattr(mt5, f"TIMEFRAME_{config.TIMEFRAME}", mt5.TIMEFRAME_M1)
```

### 5.3 `src/risk/engine.py` — Lot formula branch
```python
if config.CONTRACT_SIZE >= 100_000:  # Forex pair
    pip_size = 0.01 if "JPY" in config.SYMBOL else 0.0001
    sl_pips = abs(entry - sl) / pip_size
    lot_size = risk_amount / (sl_pips * config.PIP_VALUE_PER_LOT)
else:  # Gold / commodities: 1 lot = CONTRACT_SIZE oz
    lot_size = risk_amount / (sl_distance * config.CONTRACT_SIZE)
```

Also update `validate()` with:
1. **Pip-based SL/TP validation** for Forex (parallel to lot-size branch):
```python
if config.CONTRACT_SIZE >= 100_000:  # Forex
    pip_size = 0.01 if "JPY" in config.SYMBOL else 0.0001
    sl_pips = abs(entry - sl) / pip_size
    tp_pips = abs(tp - entry) / pip_size
    if not (config.SL_PIPS_MIN <= sl_pips <= config.SL_PIPS_MAX):
        return ValidationResult.INVALID_SL
    if tp_pips < config.SL_PIPS_MIN * config.MIN_RR_RATIO:  # use existing MIN_RR_RATIO
        return ValidationResult.INVALID_TP
else:  # Gold: existing dollar checks unchanged
    if sl_distance < config.MIN_SL_USD or sl_distance > config.MAX_SL_USD:
        return ValidationResult.INVALID_SL
    ...
```
2. **`MAX_TRADES_PER_DAY` gate** — caller passes `daily_trade_count: int` (count of trades placed today, queried from DB by `main.py` before calling validate). `validate()` signature gains `daily_trade_count: int = 0`. Gate: `if daily_trade_count >= config.MAX_TRADES_PER_DAY: return ValidationResult.MAX_TRADES_REACHED`. Daily count resets at UTC midnight, consistent with existing `_check_daily_reset()` logic.

### 5.4 `src/executor/orders.py` — Fix hardcoded SYMBOL

**Problem:** Current code has `from src.mt5_bridge.data import SYMBOL` at module level, which captures `"XAUUSD"` at import time. Even after `data.py` is patched, orders.py still passes `"XAUUSD"` to `mt5.symbol_info_tick()` and the order request.

```python
# Remove:
from src.mt5_bridge.data import SYMBOL

# Replace all uses of naked `SYMBOL` with config.SYMBOL:
from src import config

# e.g.:
tick = mt5.symbol_info_tick(config.SYMBOL)
request = {
    "symbol": config.SYMBOL,
    ...
}
```

### 5.5 `src/ai_layer/prompt.py` — Dynamic asset context
```python
from src import config

if config.CONTRACT_SIZE >= 100_000:  # Forex
    role = f"expert {config.SYMBOL} forex scalper"
    sl_guide = f"SL: {config.SL_PIPS_MIN}–{config.SL_PIPS_MAX} pips from entry"
    tp_guide = f"TP: {config.TP_PIPS_MIN}–{config.TP_PIPS_MAX} pips from entry"
    rr_guide = f"TP/SL ratio: at least {config.MIN_RR_RATIO}"
else:  # Gold
    role = f"expert gold ({config.SYMBOL}) swing trader"
    sl_guide = f"SL distance: ${config.MIN_SL_USD}–${config.MAX_SL_USD}"
    tp_guide = f"TP distance: at least ${config.MIN_TP_USD}"
    rr_guide = f"TP/SL ratio: at least {config.MIN_RR_RATIO}"
```

### 5.6 `dashboard/` — Tab switcher

**`dashboard/next.config.js`** (note: `.js`, not `.ts`): Add two rewrite rules:
```js
rewrites: async () => [
  {
    source: '/api/gold/:path*',
    destination: `${process.env.GOLD_API_URL ?? 'http://localhost:8000'}/api/:path*`,
  },
  {
    source: '/api/forex/:path*',
    destination: `${process.env.FOREX_API_URL ?? 'http://localhost:8001'}/api/:path*`,
  },
],
```
Remove (or keep as legacy fallback) the existing single rewrite to `localhost:8000`.

**`dashboard/lib/api.ts`:** All exported API functions gain a `bot: 'gold' | 'forex'` parameter. Base path is derived from bot:
```ts
const BASE = (bot: 'gold' | 'forex') => `/api/${bot}`;

export async function fetchStatus(bot: 'gold' | 'forex') { ... }
export async function fetchSignals(bot: 'gold' | 'forex') { ... }
export async function fetchTrades(bot: 'gold' | 'forex') { ... }
// ... all other functions same pattern
```

**`dashboard/components/BotTabSwitcher.tsx`:** New component — "GOLD" | "FOREX" pill tabs in StatusBar. Active bot stored in React context (`BotContext`). All API calls read `bot` from `BotContext`.

---

## 6. Database Setup

```sql
-- Creates openforex database (same schema as opengold)
CREATE DATABASE openforex OWNER opengold;
\c openforex
\i src/schema.sql
```

---

## 7. Scorer Weights for Forex Scalper

Forex scalping on M5 favors:
- `vwap` — high weight all regimes (VWAP deviation entry)
- `breakout` — high on BREAKOUT
- `scalping` — high all regimes
- `rsi`/`stochastic` — reduced (lagging on fast moves)

These can be tuned via `AGGREGATOR_WEIGHTS` env or kept symmetric for now and tuned post-launch.

---

## 8. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Gold bot breaks when config fields added | New fields all have defaults — Gold bot unaffected |
| Forex lot formula wrong → ORDER_REJECTED | Test with DRY_RUN=true first |
| Dashboard shows stale data when Forex bot offline | Show "OFFLINE" badge when API returns error |
| `main.py --env` flag not yet implemented | Must implement before Forex can start |

---

## 9. Out of Scope (Future)

- GBPUSD support (just change SYMBOL in forex.env — no code change needed)
- Crypto exchange (Binance) bridge
- Daily PnL comparison chart Gold vs Forex on dashboard
