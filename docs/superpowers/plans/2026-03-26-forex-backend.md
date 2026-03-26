# Multi-Symbol Forex Scalper — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Python backend so it can run as either a Gold bot (`--env gold.env`) or a Forex Scalper (`--env forex.env`) from the same codebase — keeping existng Gold behaviour 100% intact.

**Architecture:** Single shared codebase. CLI `--env` flag selects which profile to load before any `src.*` imports. Five Python files get targeted edits; two env files are created; a second PostgreSQL database is provisioned.

**Tech Stack:** Python 3.12, FastAPI, MetaTrader5, python-dotenv, pytest, psycopg2

**Spec:** `docs/superpowers/specs/2026-03-26-multi-symbol-forex-scalper-design.md`

**Run all tests:** `pytest tests/ -x -q`

---

## File Map

| File | Change |
|---|---|
| `src/config.py` | Add 9 new env-backed fields |
| `main.py` | Two-phase startup: argparse → load_dotenv → src imports; add daily_trade_count query |
| `src/mt5_bridge/data.py` | Replace hardcoded `SYMBOL` / `TIMEFRAME` with config values |
| `src/executor/orders.py` | Replace module-level `SYMBOL` import with `config.SYMBOL` at call time |
| `src/risk/engine.py` | Add Forex lot formula branch + pip-based `validate()` branch + `daily_trade_count` gate |
| `src/ai_layer/prompt.py` | Dynamic role / SL-TP guidance based on `config.CONTRACT_SIZE` |
| `gold.env` | Create (copied from `.env` + new fields; **add to .gitignore first**) |
| `forex.env` | Create (EURUSD scalper profile; **credentials filled manually**) |
| `tests/test_risk.py` | Add Forex-specific tests + `daily_trade_count` tests |
| `tests/test_executor_orders.py` | Add bot-aware symbol test |
| `tests/test_ai_prompt.py` | Add Forex prompt tests |

**Note on API server startup:** `uvicorn src.api.app:app` is a separate process from `main.py`. It has no `--env` flag. Launch the Forex API server by pre-setting env vars:
```bash
# Gold API (already working)
uvicorn src.api.app:app --host 127.0.0.1 --port 8000

# Forex API — env vars set inline OR in a shell export block from forex.env
export $(grep -v '^#' forex.env | xargs)
uvicorn src.api.app:app --host 127.0.0.1 --port 8001
```
This is sufficient for local dev. Docker-compose multi-service setup is out of scope for this plan (future ops work).

---

## Task 1: Extend `src/config.py` with multi-symbol fields

**Files:**
- Modify: `src/config.py`

- [ ] **Step 1: Add the 9 new fields after the `# Risk` block**

Insert the following block immediately after the existing Risk section in `src/config.py`:

```python
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
```

**Note:** `TP_PIPS_MIN` and `TP_PIPS_MAX` are referenced in `prompt.py` for the SL/TP guidance text shown to the AI. The engine's Forex TP validation uses `SL_PIPS_MIN * MIN_RR_RATIO` as the binding floor (ensuring RR ratio compliance), so `TP_PIPS_MIN` is not used in `engine.py`.

Also update `DASHBOARD_API_PORT` to respect an `API_PORT` override (add it right before or after the existing DASHBOARD_API_PORT line):

```python
# Dashboard API  (API_PORT overrides DASHBOARD_API_PORT for multi-bot support)
DASHBOARD_API_HOST = os.getenv("DASHBOARD_API_HOST", "127.0.0.1")
DASHBOARD_API_PORT = int(os.getenv("API_PORT", os.getenv("DASHBOARD_API_PORT", "8000")))
```

- [ ] **Step 2: Verify existing tests still pass**

```bash
pytest tests/ -x -q
```

Expected: all tests pass (no import errors, no new failures — the new fields all have safe defaults).

- [ ] **Step 3: Commit**

```bash
git add src/config.py
git commit -m "feat(config): add multi-symbol fields (SYMBOL, CONTRACT_SIZE, TIMEFRAME, etc.)"
```

---

## Task 2: Restructure `main.py` — two-phase startup

**Files:**
- Modify: `main.py`

**Why:** Python evaluates module-level `from src import ...` statements at import time, before `if __name__ == "__main__":` runs. The `--env` flag must be parsed and `load_dotenv` called *before* any `src.*` import so `config.py` reads the correct environment.

- [ ] **Step 1: Replace the import block at the top of `main.py`**

Replace everything from lines 1–20 (the existing import block) with this two-phase structure:

```python
import time
import logging
import argparse
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

# ── Phase 1: parse --env flag and load profile BEFORE any src.* imports ──────
# (config.py reads os.environ at import time; dotenv must run first)
_env_parser = argparse.ArgumentParser(add_help=False)
_env_parser.add_argument("--env", default=".env",
                         help="ENV profile file (e.g. gold.env or forex.env)")
_env_args, _ = _env_parser.parse_known_args()
load_dotenv(_env_args.env, override=True)

# ── Phase 2: import src modules (they now see the correct env values) ─────────
from src import config
from src.mt5_bridge.connection import connect, disconnect, is_connected, get_account_info
from src.mt5_bridge.data import fetch_candles, get_last_candle_time, get_positions, get_history_deals
from src.regime.classifier import classify as classify_regime
from src.strategies import run_all
from src.aggregator.scorer import aggregate as compute_agg
from collections import Counter
from src.risk.engine import validate
from src.executor.orders import place_order, sync_positions
from src.logger.writer import (
    log_decision, log_trade,
    get_kill_switch_state, set_kill_switch,
    get_daily_start_balance, set_daily_start_balance,
    check_and_log_trade_no_duplicate,
)
from src.journal.reader import get_journal_context
from src.ai_layer.prompt import build_prompt
from src.ai_layer.client import decide
from src.db import execute
```

- [ ] **Step 2: Update `main()` to show the active profile in startup log**

Replace the existing `main()` function's first logger line:

```python
def main():
    parser = argparse.ArgumentParser(description="OpenGold/OpenForex trading bot")
    parser.add_argument("--env", default=".env",
                        help="ENV profile file (e.g. gold.env or forex.env)")
    args = parser.parse_args()
    logger.info(f"Bot starting… [profile={args.env}] [symbol={config.SYMBOL}] [db={config.DB_NAME}]")
    if not connect_with_retry(config.MT5_RECONNECT_RETRIES):
        logger.critical("Cannot connect to MT5 after retries. Exiting.")
        return
    if config.DRY_RUN:
        logger.warning("*** DRY_RUN MODE — orders will NOT be sent to MT5 ***")
    run_loop()
```

- [ ] **Step 3: Verify argparse works (smoke test)**

```bash
python main.py --help
```

Expected output includes `--env` flag description. No MT5 connection attempt happens.

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat(main): two-phase startup — --env flag loads dotenv before src imports"
```

---

## Task 3: De-hardcode `src/mt5_bridge/data.py`

**Files:**
- Modify: `src/mt5_bridge/data.py`

- [ ] **Step 1: Replace hardcoded SYMBOL and TIMEFRAME**

Replace the two module-level lines:

```python
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M1
```

With:

```python
from src import config

SYMBOL = config.SYMBOL
TIMEFRAME = getattr(mt5, f"TIMEFRAME_{config.TIMEFRAME}", mt5.TIMEFRAME_M1)
```

Note: `SYMBOL` is kept as a module-level constant for backward compatibility (some code outside orders.py may reference it). `orders.py` will be updated in Task 4 to use `config.SYMBOL` directly.

- [ ] **Step 2: Verify syntax**

```bash
python -c "import ast; ast.parse(open('src/mt5_bridge/data.py').read()); print('syntax ok')"
```

Expected: `syntax ok`

- [ ] **Step 3: Run existing tests**

```bash
pytest tests/ -x -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/mt5_bridge/data.py
git commit -m "feat(data): SYMBOL and TIMEFRAME from config — not hardcoded"
```

---

## Task 4: Fix `src/executor/orders.py` — dynamic symbol

**Files:**
- Modify: `src/executor/orders.py`

**Why:** The current `from src.mt5_bridge.data import SYMBOL` captures `"XAUUSD"` at import time. Even after `data.py` is patched, orders placed for Forex would still use the Gold symbol.

- [ ] **Step 1: Replace module-level SYMBOL import with config reference**

Replace:

```python
from src.mt5_bridge.data import SYMBOL
```

With:

```python
from src import config
```

Then replace every use of the bare name `SYMBOL` in the file with `config.SYMBOL`. There are two occurrences in `place_order`:

```python
tick = mt5.symbol_info_tick(config.SYMBOL)
```

```python
request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": config.SYMBOL,
    ...
}
```

- [ ] **Step 2: Write a unit test for the dynamic symbol**

Add to **`tests/test_executor_orders.py`** (extend the existing file — do not create a new one):

```python
import pytest
from unittest.mock import patch, MagicMock
from src import config


def test_place_order_uses_config_symbol(monkeypatch):
    """place_order must use config.SYMBOL, not a hardcoded constant."""
    monkeypatch.setattr(config, "SYMBOL", "EURUSD")

    mock_tick = MagicMock()
    mock_tick.ask = 1.08500
    mock_tick.bid = 1.08490

    mock_result = MagicMock()
    mock_result.retcode = 10009   # TRADE_RETCODE_DONE
    mock_result.order = 12345
    mock_result.price = 1.08500

    with patch("src.executor.orders.mt5") as mock_mt5:
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.ORDER_FILLING_IOC = 1
        mock_mt5.TRADE_RETCODE_DONE = 10009
        mock_mt5.symbol_info_tick.return_value = mock_tick
        mock_mt5.order_send.return_value = mock_result

        from src.executor.orders import place_order
        result = place_order("BUY", 0.10, 1.0810, 1.0900, dry_run=False)

    assert result["success"] is True
    call_args = mock_mt5.order_send.call_args[0][0]
    assert call_args["symbol"] == "EURUSD"
```

- [ ] **Step 3: Run the new test (verify it fails before implementation)**

```bash
pytest tests/test_orders.py -v
```

Expected: FAIL (SYMBOL still hardcoded or test file doesn't exist yet — confirm the test runner finds it).

- [ ] **Step 4: Run test after implementation**

```bash
pytest tests/test_orders.py -v
```

Expected: PASS.

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -x -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/executor/orders.py tests/test_orders.py
git commit -m "feat(orders): use config.SYMBOL instead of hardcoded XAUUSD"
```

---

## Task 5: Update `src/risk/engine.py` — Forex lot formula + pip validation + daily gate

**Files:**
- Modify: `src/risk/engine.py`
- Modify: `tests/test_risk.py`

- [ ] **Step 1: Write the new failing tests first**

Append these tests to the end of `tests/test_risk.py`:

```python
from src import config as _config


# ── Forex (EURUSD) tests ──────────────────────────────────────────────────────

def test_forex_valid_buy_passes(monkeypatch):
    """EURUSD buy with 4-pip SL and 5-pip TP should be approved."""
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100_000)
    monkeypatch.setattr(_config, "SYMBOL", "EURUSD")
    monkeypatch.setattr(_config, "PIP_VALUE_PER_LOT", 10.0)
    monkeypatch.setattr(_config, "SL_PIPS_MIN", 3.0)
    monkeypatch.setattr(_config, "SL_PIPS_MAX", 5.0)
    monkeypatch.setattr(_config, "MIN_RR_RATIO", 1.3)
    # entry=1.08500, sl=1.08460 (4 pips), tp=1.08550 (5 pips)
    # RR check: 5 >= SL_PIPS_MIN(3) * MIN_RR_RATIO(1.3) = 3.9 ✓
    result = validate(
        action="BUY", confidence=0.8,
        sl=1.08460, tp=1.08550,
        entry=1.08500,
        balance=10000.0, open_trades=0, kill_switch=False,
    )
    assert result.approved
    assert result.lot_size > 0


def test_forex_lot_size_correct(monkeypatch):
    """Forex lot = risk_amount / (sl_pips * pip_value_per_lot)."""
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100_000)
    monkeypatch.setattr(_config, "SYMBOL", "EURUSD")
    monkeypatch.setattr(_config, "PIP_VALUE_PER_LOT", 10.0)
    monkeypatch.setattr(_config, "RISK_PER_TRADE", 0.01)
    monkeypatch.setattr(_config, "SL_PIPS_MIN", 3.0)
    monkeypatch.setattr(_config, "SL_PIPS_MAX", 5.0)
    monkeypatch.setattr(_config, "MIN_RR_RATIO", 1.3)
    # risk=$100 (1% of $10000), SL=4 pips, PipValue=$10 → lot=100/(4*10)=2.50
    result = validate(
        action="BUY", confidence=0.8,
        sl=1.08460, tp=1.08550,
        entry=1.08500,
        balance=10000.0, open_trades=0, kill_switch=False,
    )
    assert result.lot_size == 2.50


def test_forex_sl_too_tight_blocked(monkeypatch):
    """SL < SL_PIPS_MIN should return INVALID_SL for Forex."""
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100_000)
    monkeypatch.setattr(_config, "SYMBOL", "EURUSD")
    monkeypatch.setattr(_config, "PIP_VALUE_PER_LOT", 10.0)
    monkeypatch.setattr(_config, "SL_PIPS_MIN", 3.0)
    monkeypatch.setattr(_config, "SL_PIPS_MAX", 5.0)
    monkeypatch.setattr(_config, "MIN_RR_RATIO", 1.3)
    # SL = 2 pips (below SL_PIPS_MIN=3)
    result = validate(
        action="BUY", confidence=0.9,
        sl=1.08480, tp=1.08550,   # 2 pips SL, 7 pips TP
        entry=1.08500,
        balance=10000.0, open_trades=0, kill_switch=False,
    )
    assert not result.approved
    assert result.block_reason == "INVALID_SL"


def test_forex_sl_too_wide_blocked(monkeypatch):
    """SL > SL_PIPS_MAX should return INVALID_SL for Forex."""
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100_000)
    monkeypatch.setattr(_config, "SYMBOL", "EURUSD")
    monkeypatch.setattr(_config, "PIP_VALUE_PER_LOT", 10.0)
    monkeypatch.setattr(_config, "SL_PIPS_MIN", 3.0)
    monkeypatch.setattr(_config, "SL_PIPS_MAX", 5.0)
    monkeypatch.setattr(_config, "MIN_RR_RATIO", 1.3)
    # SL = 8 pips (above SL_PIPS_MAX=5)
    result = validate(
        action="BUY", confidence=0.9,
        sl=1.08420, tp=1.08600,   # 8 pips SL
        entry=1.08500,
        balance=10000.0, open_trades=0, kill_switch=False,
    )
    assert not result.approved
    assert result.block_reason == "INVALID_SL"


def test_forex_tp_fails_rr_ratio(monkeypatch):
    """TP that doesn't satisfy MIN_RR_RATIO should return INVALID_TP for Forex."""
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100_000)
    monkeypatch.setattr(_config, "SYMBOL", "EURUSD")
    monkeypatch.setattr(_config, "PIP_VALUE_PER_LOT", 10.0)
    monkeypatch.setattr(_config, "SL_PIPS_MIN", 3.0)
    monkeypatch.setattr(_config, "SL_PIPS_MAX", 5.0)
    monkeypatch.setattr(_config, "MIN_RR_RATIO", 1.3)
    # SL=4 pips, TP=3 pips → tp_pips(3) < SL_PIPS_MIN(3)*MIN_RR_RATIO(1.3)=3.9 → INVALID_TP
    result = validate(
        action="BUY", confidence=0.9,
        sl=1.08460, tp=1.08530,   # 4-pip SL, 3-pip TP
        entry=1.08500,
        balance=10000.0, open_trades=0, kill_switch=False,
    )
    assert not result.approved
    assert result.block_reason == "INVALID_TP"


def test_daily_trade_limit_blocks(monkeypatch):
    """When daily_trade_count >= MAX_TRADES_PER_DAY, validate should block."""
    monkeypatch.setattr(_config, "MAX_TRADES_PER_DAY", 5)
    result = validate(
        action="BUY", confidence=0.9,
        sl=1910.0, tp=1940.0,
        entry=1920.0, balance=10000.0,
        open_trades=0, kill_switch=False,
        daily_trade_count=5,
    )
    assert not result.approved
    assert result.block_reason == "DAILY_TRADE_LIMIT"


def test_daily_trade_limit_not_triggered_below_max(monkeypatch):
    """daily_trade_count < MAX_TRADES_PER_DAY should not block (Gold trade)."""
    monkeypatch.setattr(_config, "MAX_TRADES_PER_DAY", 15)
    result = validate(
        action="BUY", confidence=0.8,
        sl=1910.0, tp=1940.0,
        entry=1920.0, balance=10000.0,
        open_trades=0, kill_switch=False,
        daily_trade_count=14,
    )
    assert result.approved


def test_gold_lot_formula_unaffected(monkeypatch):
    """Gold lot formula (CONTRACT_SIZE=100) must be unaffected by multi-symbol changes."""
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100)
    monkeypatch.setattr(_config, "RISK_PER_TRADE", 0.01)
    # risk=$100, SL=$10, lot = 100/(10*100) = 0.10
    result = validate(
        action="BUY", confidence=0.9,
        sl=1910.0, tp=1940.0,
        entry=1920.0, balance=10000.0,
        open_trades=0, kill_switch=False,
    )
    assert result.approved
    assert result.lot_size == 0.10
```

- [ ] **Step 2: Run tests to confirm they FAIL**

```bash
pytest tests/test_risk.py::test_forex_valid_buy_passes tests/test_risk.py::test_daily_trade_limit_blocks -v
```

Expected: FAIL (functions don't accept `daily_trade_count` yet; Forex branch doesn't exist).

- [ ] **Step 3: Implement the new `validate()` in `src/risk/engine.py`**

Replace the entire `validate()` function with:

```python
def validate(
    action: str,
    confidence: float,
    sl: float,
    tp: float,
    entry: float,
    balance: float,
    open_trades: int,
    kill_switch: bool,
    daily_trade_count: int = 0,
) -> RiskResult:
    if kill_switch:
        return RiskResult(approved=False, block_reason="KILL_SWITCH_ACTIVE")
    if open_trades >= config.MAX_CONCURRENT_TRADES:
        return RiskResult(approved=False, block_reason="MAX_TRADES_REACHED")
    if daily_trade_count >= config.MAX_TRADES_PER_DAY:
        return RiskResult(approved=False, block_reason="DAILY_TRADE_LIMIT")
    if confidence < config.MIN_AI_CONFIDENCE:
        return RiskResult(approved=False, block_reason="LOW_CONFIDENCE")

    sl_distance = abs(entry - sl)
    risk_amount = balance * config.RISK_PER_TRADE

    if config.CONTRACT_SIZE >= 100_000:  # Forex pair
        pip_size = 0.01 if "JPY" in config.SYMBOL else 0.0001
        sl_pips = sl_distance / pip_size
        tp_pips = abs(tp - entry) / pip_size
        if not (config.SL_PIPS_MIN <= sl_pips <= config.SL_PIPS_MAX):
            return RiskResult(approved=False, block_reason="INVALID_SL")
        if tp_pips < config.SL_PIPS_MIN * config.MIN_RR_RATIO:
            return RiskResult(approved=False, block_reason="INVALID_TP")
        lot_size = risk_amount / (sl_pips * config.PIP_VALUE_PER_LOT)
    else:  # Gold / commodities: 1 lot = CONTRACT_SIZE oz
        if sl_distance < config.MIN_SL_USD or sl_distance > config.MAX_SL_USD:
            return RiskResult(approved=False, block_reason="INVALID_SL")
        tp_distance = abs(tp - entry)
        if tp_distance < config.MIN_TP_USD:
            return RiskResult(approved=False, block_reason="INVALID_TP")
        if sl_distance > 0 and (tp_distance / sl_distance) < config.MIN_RR_RATIO:
            return RiskResult(approved=False, block_reason="LOW_RR_RATIO")
        # Note: config.CONTRACT_SIZE replaces the old hardcoded 100 — default is 100 (Gold)
        lot_size = risk_amount / (sl_distance * config.CONTRACT_SIZE)

    lot_size = (lot_size // LOT_STEP) * LOT_STEP
    if lot_size < MIN_LOT:
        return RiskResult(approved=False, block_reason="BELOW_MIN_LOT")

    return RiskResult(approved=True, lot_size=round(lot_size, 2))
```

- [ ] **Step 4: Run all risk tests**

```bash
pytest tests/test_risk.py -v
```

Expected: all pass, including original Gold tests.

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -x -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/risk/engine.py tests/test_risk.py
git commit -m "feat(risk): Forex lot formula + pip-based SL/TP validation + MAX_TRADES_PER_DAY gate"
```

> **Additional test cases to include in `tests/test_risk.py` (append alongside the above):**
>
> ```python
> def test_gold_lot_uses_contract_size(monkeypatch):
>     """Gold branch: lot = risk / (sl_distance * CONTRACT_SIZE). Regression for hardcode removal."""
>     monkeypatch.setattr(_config, "CONTRACT_SIZE", 100)
>     monkeypatch.setattr(_config, "RISK_PER_TRADE", 0.01)
>     # risk=$100, SL=$10, lot=100/(10*100)=0.10
>     result = validate(
>         action="BUY", confidence=0.9,
>         sl=1910.0, tp=1940.0,
>         entry=1920.0, balance=10000.0,
>         open_trades=0, kill_switch=False,
>     )
>     assert result.lot_size == 0.10
>
> def test_forex_jpy_pip_size(monkeypatch):
>     """JPY pairs use pip_size=0.01, not 0.0001."""
>     monkeypatch.setattr(_config, "CONTRACT_SIZE", 100_000)
>     monkeypatch.setattr(_config, "SYMBOL", "USDJPY")
>     monkeypatch.setattr(_config, "PIP_VALUE_PER_LOT", 9.0)  # ~$9/pip for USDJPY
>     monkeypatch.setattr(_config, "SL_PIPS_MIN", 3.0)
>     monkeypatch.setattr(_config, "SL_PIPS_MAX", 5.0)
>     monkeypatch.setattr(_config, "MIN_RR_RATIO", 1.3)
>     # entry=150.000, sl=149.960 (4 JPY pips = 0.04), tp=150.050 (5 JPY pips = 0.05)
>     result = validate(
>         action="BUY", confidence=0.8,
>         sl=149.960, tp=150.050,
>         entry=150.000,
>         balance=10000.0, open_trades=0, kill_switch=False,
>     )
>     assert result.approved
>
> def test_daily_trade_limit_default_does_not_block():
>     """Default MAX_TRADES_PER_DAY=999 should not block a normal 10-trade day."""
>     result = validate(
>         action="BUY", confidence=0.9,
>         sl=1910.0, tp=1940.0,
>         entry=1920.0, balance=10000.0,
>         open_trades=0, kill_switch=False,
>         daily_trade_count=10,
>     )
>     assert result.approved  # 10 < 999 default
> ```

---

## Task 6: Wire `daily_trade_count` into `main.py` run loop

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Add daily_trade_count query before `validate()` call**

In `run_loop()`, find the section `# ── Phase 3: journal → AI → risk ───` and before the `risk = validate(...)` call, add:

```python
            # Query today's placed trades for MAX_TRADES_PER_DAY gate
            try:
                rows = execute(
                    "SELECT COUNT(*) FROM trades "
                    "WHERE DATE(open_time AT TIME ZONE 'UTC') = current_date",
                    fetch=True,
                )
                daily_trade_count = int(rows[0][0]) if rows else 0
            except Exception:
                daily_trade_count = 0  # be permissive on DB error
```

- [ ] **Step 2: Pass `daily_trade_count` to `validate()`**

Update the `validate()` call to include the new parameter:

```python
            risk = validate(
                action=direction,
                confidence=confidence,
                sl=sl,
                tp=tp,
                entry=price,
                balance=balance,
                open_trades=open_trades,
                kill_switch=kill,
                daily_trade_count=daily_trade_count,
            )
```

- [ ] **Step 3: Verify syntax**

```bash
python -c "import ast; ast.parse(open('main.py').read()); print('syntax ok')"
```

Expected: `syntax ok`

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat(main): pass daily_trade_count to validate for MAX_TRADES_PER_DAY gate"
```

---

## Task 7: Update `src/ai_layer/prompt.py` — dynamic asset context

**Files:**
- Modify: `src/ai_layer/prompt.py`
- Modify: `tests/test_ai_prompt.py`

- [ ] **Step 1: Write failing tests first**

Append to `tests/test_ai_prompt.py`:

```python
from src import config as _config


def test_gold_prompt_mentions_gold_role(monkeypatch):
    """Gold mode prompt describes a gold swing trader role."""
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100)
    monkeypatch.setattr(_config, "SYMBOL", "XAUUSD")
    result = build_prompt(
        journal="",
        regime="TRENDING_UP",
        buy_avg=7.0, sell_avg=2.0,
        buy_peak=8.0, sell_peak=3.0,
        window_minutes=5,
        price=1923.45,
        atr=12.55,
    )
    assert "gold" in result.lower()
    assert "XAUUSD" in result


def test_forex_prompt_mentions_forex_role(monkeypatch):
    """Forex mode prompt describes a forex scalper role."""
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100_000)
    monkeypatch.setattr(_config, "SYMBOL", "EURUSD")
    monkeypatch.setattr(_config, "SL_PIPS_MIN", 3.0)
    monkeypatch.setattr(_config, "SL_PIPS_MAX", 5.0)
    monkeypatch.setattr(_config, "TP_PIPS_MIN", 4.0)
    monkeypatch.setattr(_config, "TP_PIPS_MAX", 5.0)
    monkeypatch.setattr(_config, "MIN_RR_RATIO", 1.3)
    result = build_prompt(
        journal="",
        regime="BREAKOUT",
        buy_avg=7.0, sell_avg=2.0,
        buy_peak=8.0, sell_peak=3.0,
        window_minutes=3,
        price=1.08500,
        atr=0.00120,
    )
    assert "forex" in result.lower() or "EURUSD" in result
    assert "pips" in result.lower()


def test_forex_prompt_uses_correct_price_format(monkeypatch):
    """Forex price should appear with 5 decimal places."""
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100_000)
    monkeypatch.setattr(_config, "SYMBOL", "EURUSD")
    monkeypatch.setattr(_config, "SL_PIPS_MIN", 3.0)
    monkeypatch.setattr(_config, "SL_PIPS_MAX", 5.0)
    monkeypatch.setattr(_config, "TP_PIPS_MIN", 4.0)
    monkeypatch.setattr(_config, "TP_PIPS_MAX", 5.0)
    monkeypatch.setattr(_config, "MIN_RR_RATIO", 1.3)
    result = build_prompt(
        journal="",
        regime="BREAKOUT",
        buy_avg=7.0, sell_avg=2.0,
        buy_peak=8.0, sell_peak=3.0,
        window_minutes=3,
        price=1.08500,
        atr=0.00120,
    )
    assert "1.08500" in result
```

- [ ] **Step 2: Run tests to confirm they FAIL**

```bash
pytest tests/test_ai_prompt.py::test_forex_prompt_mentions_forex_role -v
```

Expected: FAIL (no Forex branch in prompt.py yet).

- [ ] **Step 3: Replace `build_prompt()` in `src/ai_layer/prompt.py`**

```python
from src import config


def build_prompt(
    journal: str,
    regime: str,
    buy_avg: float,
    sell_avg: float,
    buy_peak: float,
    sell_peak: float,
    window_minutes: int,
    price: float,
    atr: float,
) -> str:
    """Build the Claude prompt from market context and trade journal."""
    sections = []

    if journal:
        sections.append(f"[JOURNAL]\n{journal}")

    if config.CONTRACT_SIZE >= 100_000:  # Forex
        price_str = f"{price:.5f}"
        atr_str = f"{atr:.5f}"
    else:  # Gold
        price_str = f"{price:.2f}"
        atr_str = f"{atr:.2f}"

    sections.append(
        f"[MARKET — {window_minutes}-min window]\n"
        f"Dominant regime: {regime} | Price: {price_str} | ATR(14): {atr_str}\n"
        f"Avg  — buy: {buy_avg:.1f}, sell: {sell_avg:.1f}\n"
        f"Peak — buy: {buy_peak:.1f}, sell: {sell_peak:.1f}"
    )

    if config.CONTRACT_SIZE >= 100_000:  # Forex
        role = f"expert {config.SYMBOL} forex scalper"
        rr_example_sl = config.SL_PIPS_MIN
        rr_example_tp = rr_example_sl * config.MIN_RR_RATIO
        risk_constraints = (
            f"- SL distance: {config.SL_PIPS_MIN}–{config.SL_PIPS_MAX} pips from entry\n"
            f"- TP distance: at least {config.TP_PIPS_MIN} pips from entry\n"
            f"- TP/SL ratio: at least {config.MIN_RR_RATIO} "
            f"(e.g. if SL={rr_example_sl:.0f} pips, TP must be >={rr_example_tp:.1f} pips)"
        )
    else:  # Gold
        role = f"expert gold ({config.SYMBOL}) swing trader"
        risk_constraints = (
            f"- SL distance from entry: ${config.MIN_SL_USD}–${config.MAX_SL_USD}\n"
            f"- TP distance from entry: at least ${config.MIN_TP_USD}\n"
            f"- TP/SL ratio: at least {config.MIN_RR_RATIO} "
            f"(e.g. if SL=$10, TP must be >=${10 * config.MIN_RR_RATIO:.0f})"
        )

    sections.append(
        f"[TASK]\n"
        f"You are an {role}. Based on the market context above, "
        "decide the next trade action.\n"
        "Reply with ONLY valid JSON (no markdown, no explanation):\n"
        '{"action": "BUY"|"SELL"|"SKIP", "confidence": 0.0-1.0, '
        '"sl": <stop_loss_price>, "tp": <take_profit_price>, '
        '"reasoning": "<one sentence explaining your decision>"}\n'
        f"Risk constraints (your SL/TP MUST satisfy these or the trade will be rejected):\n"
        f"{risk_constraints}\n"
        "If uncertain or conditions are unfavourable, use SKIP."
    )

    return "\n\n".join(sections)
```

- [ ] **Step 4: Run all prompt tests**

```bash
pytest tests/test_ai_prompt.py -v
```

Expected: all pass.

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -x -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/ai_layer/prompt.py tests/test_ai_prompt.py
git commit -m "feat(prompt): dynamic role and SL/TP guidance based on CONTRACT_SIZE"
```

---

## Task 8: Create env files — `gold.env` and `forex.env`

**Files:**
- Create: `gold.env`
- Create: `forex.env`

- [ ] **Step 1: Add .gitignore entries FIRST (before creating any env files)**

Verify and update `.gitignore` so credentials never enter git history:

```bash
# Check current state
grep -E '(gold|forex|\.env)' .gitignore
```

If `*.env` or both `gold.env` and `forex.env` are not present, add them:

```
# ENV profiles (contain credentials)
gold.env
forex.env
```

Commit this change before proceeding:

```bash
git add .gitignore
git commit -m "chore: gitignore gold.env and forex.env (contain credentials)"
```

- [ ] **Step 2: Create `gold.env`** (COPY not mv — keep `.env` for default behaviour)

```bash
cp .env gold.env
```

Then add these lines to the bottom of `gold.env` (they're already correct defaults but mark them explicitly):

```ini
# Multi-symbol identity (added for explicitness — these are the defaults)
BOT_ID=gold
SYMBOL=XAUUSD
TIMEFRAME=M1
CONTRACT_SIZE=100
API_PORT=8000
MAX_TRADES_PER_DAY=999
```

- [ ] **Step 2: Create `forex.env`**

Create a new file `forex.env` with these contents (fill in MT5 credentials from your existing `.env`):

```ini
# ── MT5 credentials (same as gold.env) ───────────────────────────────────────
MT5_LOGIN=<your_login>
MT5_PASSWORD=<your_password>
MT5_SERVER=<your_server>

# ── Database ──────────────────────────────────────────────────────────────────
DB_HOST=localhost
DB_PORT=5432
DB_NAME=openforex
DB_USER=opengold
DB_PASSWORD=<your_db_password>

# ── AI ────────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY=<your_api_key>
CLAUDE_PRIMARY_MODEL=claude-haiku-4-5
CLAUDE_FALLBACK_MODEL=claude-sonnet-4-5

# ── Multi-symbol identity ─────────────────────────────────────────────────────
BOT_ID=forex
SYMBOL=EURUSD
TIMEFRAME=M5
CONTRACT_SIZE=100000
PIP_VALUE_PER_LOT=10
API_PORT=8001

# ── Risk ──────────────────────────────────────────────────────────────────────
RISK_PER_TRADE=0.01
MAX_CONCURRENT_TRADES=3
DAILY_DRAWDOWN_LIMIT=0.03
MIN_AI_CONFIDENCE=0.75
SL_PIPS_MIN=3
SL_PIPS_MAX=5
TP_PIPS_MIN=4
TP_PIPS_MAX=5
MIN_RR_RATIO=1.3
MAX_TRADES_PER_DAY=15

# ── Trigger ───────────────────────────────────────────────────────────────────
TRIGGER_MIN_SCORE=4.0
TRIGGER_MIN_SCORE_DIFF=1.5
AI_INTERVAL_MINUTES=1

# ── Sessions (London 07:00–16:59 UTC; end is exclusive) ─────────────────────
TRADE_SESSIONS_UTC=7-17

# ── System ────────────────────────────────────────────────────────────────────
DRY_RUN=true
POLL_INTERVAL_SECONDS=5
MT5_RECONNECT_RETRIES=3
MT5_RECONNECT_DELAY_BASE=2
```

- [ ] **Step 3: Add both env files to `.gitignore`**

Verify that `.gitignore` already excludes `*.env` or `gold.env` / `forex.env`. If not, add:

```
gold.env
forex.env
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "feat(config): add gold.env and forex.env profiles (secrets excluded from git)"
```

(Do NOT commit the actual gold.env or forex.env files if they contain credentials.)

---

## Task 9: Create `openforex` PostgreSQL database

**Files:**
- No code changes — SQL commands only

- [ ] **Step 1: Create the openforex database**

```bash
psql -U opengold -d postgres -c "CREATE DATABASE openforex OWNER opengold;"
```

Expected: `CREATE DATABASE`

- [ ] **Step 2: Apply the schema**

```bash
psql -U opengold -d openforex -f src/schema.sql
```

Expected: No error. Tables (`decisions`, `trades`, `bot_state`, etc.) created in `openforex`.

- [ ] **Step 3: Verify**

```bash
psql -U opengold -d openforex -c "\dt"
```

Expected: list of tables matching the `opengold` database.

- [ ] **Step 4: Commit (schema only, not credentials)**

```bash
git commit --allow-empty -m "ops: created openforex DB — same schema as opengold"
```

---

## Task 10: Gold bot smoke test with `gold.env`

This is a manual verification step to confirm the Gold bot is unbroken.

- [ ] **Step 1: Run with `--env gold.env` in DRY_RUN mode**

```bash
python main.py --env gold.env
```

Expected in first 30 seconds:
- Log line: `Bot starting… [profile=gold.env] [symbol=XAUUSD] [db=opengold]`
- MT5 connects successfully
- Candle loop starts (regime + scores printed)
- No import errors, no AttributeError on config

- [ ] **Step 2: Stop with Ctrl+C — verify clean shutdown**

Expected: `OpenGold stopped.` (or bot name equivalent)

- [ ] **Step 3: Commit final verification note**

```bash
git commit --allow-empty -m "verified: gold.env smoke test passes — bot unaffected by multi-symbol changes"
```

---

## Completion Checklist

- [ ] `src/config.py` has 9 new fields, all with safe defaults for Gold
- [ ] `main.py` two-phase: `load_dotenv(--env)` before all `src.*` imports
- [ ] `main.py` `validate()` call includes `daily_trade_count`
- [ ] `src/mt5_bridge/data.py` uses `config.SYMBOL` / `config.TIMEFRAME`
- [ ] `src/executor/orders.py` uses `config.SYMBOL` in every MT5 call
- [ ] `src/risk/engine.py` Forex branch in both lot formula and `validate()`
- [ ] `src/ai_layer/prompt.py` dynamic role for Forex vs Gold
- [ ] `gold.env` and `forex.env` files exist (not committed with secrets)
- [ ] `openforex` PostgreSQL database exists with schema applied
- [ ] `pytest tests/ -x -q` passes with zero failures
