# OpenGold Phase 4 — Live MT5 + Production Hardening

**Date:** 2026-03-25
**Author:** Teerawut Sangkakaro
**Status:** Approved
**Prior phases:** Phase 1+2 (v0.1.0-core), Phase 3 AI integration (v0.2.0-ai)

---

## 1. Overview

Phase 4 makes OpenGold production-ready on the live demo account. It adds:

1. **DRY_RUN mode** — all pipeline logic runs against real MT5 data, but `place_order` logs instead of sending to the broker. A single env-var flip enables live trading.
2. **In-loop MT5 reconnect** — when the connection drops mid-run, the bot attempts bounded reconnect with exponential backoff before resuming, rather than crashing.
3. **Configurable reconnect parameters** — retries and base delay are env-var controlled.
4. **Unit tests for MT5 bridge and executor** — mock-based, runs without a live terminal, reaching 131 total tests.

---

## 2. Config Changes (`src/config.py`)

Add after the existing `POLL_INTERVAL_SECONDS` block:

```python
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
MT5_RECONNECT_RETRIES = int(os.getenv("MT5_RECONNECT_RETRIES", "3"))
MT5_RECONNECT_DELAY_BASE = int(os.getenv("MT5_RECONNECT_DELAY_BASE", "2"))
```

Add to `.env.example`:
```
DRY_RUN=false
MT5_RECONNECT_RETRIES=3
MT5_RECONNECT_DELAY_BASE=2
```

Logging warning if `DRY_RUN=true` at startup so the operator knows they are not sending real orders.

---

## 3. DRY_RUN in `place_order` (`src/executor/orders.py`)

Add `dry_run: bool = False` parameter:

```python
def place_order(direction: str, lot_size: float, sl: float, tp: float, dry_run: bool = False) -> dict:
    if dry_run:
        logger.info(f"DRY_RUN order: {direction} {lot_size} lots sl={sl} tp={tp}")
        return {"success": True, "ticket": 0, "price": 0.0, "dry_run": True}
    # ... existing real order code unchanged
```

`main.py` call site becomes:
```python
order = place_order(direction, risk.lot_size, sl, tp, dry_run=config.DRY_RUN)
```

The result dict now carries an optional `"dry_run": True` key when in dry-run mode. The `log_decision` call is unchanged — the decision is logged the same way regardless.

---

## 4. In-Loop Reconnect (`main.py` → `run_loop`)

When `fetch_candles()` returns an empty DataFrame, the bot currently sleeps and retries. In Phase 4, it first checks whether the MT5 connection has dropped and attempts reconnect before sleeping.

```python
if candles.empty:
    if not is_connected():
        logger.warning("MT5 connection lost — attempting reconnect")
        if connect_with_retry(config.MT5_RECONNECT_RETRIES):
            logger.info("Reconnected — reconciling missed closes")
            _reconcile_missed_closes()
        else:
            logger.error("Reconnect failed — will retry next candle")
    time.sleep(config.POLL_INTERVAL_SECONDS)
    continue
```

`connect_with_retry` already uses exponential backoff (`2 ** (attempt + 1)` seconds: 2s, 4s, 8s). `MT5_RECONNECT_DELAY_BASE` makes the multiplier configurable:

```python
def connect_with_retry(retries: int = 3) -> bool:
    for attempt in range(retries):
        if connect():
            return True
        wait = config.MT5_RECONNECT_DELAY_BASE ** (attempt + 1)
        logger.warning(f"MT5 connect attempt {attempt + 1} failed — retrying in {wait}s")
        time.sleep(wait)
    return False
```

The `config.MT5_RECONNECT_RETRIES` default of 3 produces max wait of 2+4+8 = 14 seconds before giving up on the current candle, matching the user-selected strategy (b).

---

## 5. Startup DRY_RUN Warning

In `main()`, after successful connect:

```python
if config.DRY_RUN:
    logger.warning("*** DRY_RUN MODE — orders will NOT be sent to MT5 ***")
```

---

## 6. Test Coverage

### 6a. `tests/test_mt5_connection.py` — 5 tests

All tests patch `src.mt5_bridge.connection.mt5` at the module level.

| Test | What it checks |
|---|---|
| `test_connect_success` | `mt5.initialize` returns True → `connect()` returns True |
| `test_connect_failure` | `mt5.initialize` returns False → `connect()` returns False, logs error |
| `test_disconnect_calls_shutdown` | `disconnect()` calls `mt5.shutdown()` once |
| `test_is_connected_true` | `mt5.account_info()` returns MagicMock → `is_connected()` is True |
| `test_get_account_info_fields` | `mt5.account_info()` returns mock with balance/equity/currency → dict has correct keys |

### 6b. `tests/test_mt5_data.py` — 5 tests

All tests patch `src.mt5_bridge.data.mt5`.

| Test | What it checks |
|---|---|
| `test_fetch_candles_returns_dataframe` | `copy_rates_from_pos` returns valid array → DataFrame with expected columns |
| `test_fetch_candles_empty_on_none` | `copy_rates_from_pos` returns None → empty DataFrame |
| `test_get_last_candle_time_returns_datetime` | returns a single rate → result is a datetime |
| `test_get_positions_returns_list` | mock positions → list of dicts with direction/volume/ticket |
| `test_get_history_deals_filters_symbol` | deals include wrong symbol → filtered out |

### 6c. `tests/test_executor_orders.py` — 5 tests

All tests patch `src.executor.orders.mt5`.

| Test | What it checks |
|---|---|
| `test_place_order_dry_run` | `dry_run=True` → returns `{"success": True, "dry_run": True}`, `order_send` never called |
| `test_place_order_buy_success` | `order_send` returns mock with `retcode=TRADE_RETCODE_DONE` → `success=True, ticket=<n>` |
| `test_place_order_sell_success` | SELL uses `bid` price, same success path |
| `test_place_order_rejected` | `order_send` returns mock with non-DONE retcode → `success=False` |
| `test_place_order_no_tick` | `symbol_info_tick` returns None → `success=False, comment="no tick data"` |

**Total new tests: 15. Expected final count: 116 + 15 = 131 passed.**

---

## 7. `.env.example` additions

```
# Phase 4: Production mode
DRY_RUN=false
MT5_RECONNECT_RETRIES=3
MT5_RECONNECT_DELAY_BASE=2
```

---

## 8. Tag

After all tests pass: `git tag v0.3.0-live`

---

## 9. Out of Scope for Phase 4

- Trade position monitoring / trailing stop (future phase)
- Telegram/email alerts on errors (future phase)
- Dashboard / web UI (future phase)
- Multiple symbols (XAUUSD only, by design)
