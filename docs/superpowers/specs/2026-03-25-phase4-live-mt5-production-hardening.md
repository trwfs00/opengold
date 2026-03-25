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

When `fetch_candles()` returns an empty DataFrame, the bot first checks whether the MT5 connection has dropped and attempts reconnect before sleeping.

```python
if candles.empty:
    if not is_connected():
        logger.warning("MT5 connection lost — attempting reconnect")
        if connect_with_retry(config.MT5_RECONNECT_RETRIES):
            logger.info("Reconnected — reconciling missed closes")
            _reconcile_missed_closes()
        else:
            logger.error("Reconnect failed — will retry next candle")
    # If is_connected() is True but candles are still empty (e.g., market closed,
    # symbol holiday, weekend), the reconnect block is skipped and the loop sleeps
    # normally — this is intentional.
    time.sleep(config.POLL_INTERVAL_SECONDS)
    continue
```

`connect_with_retry` uses exponential backoff and replaces the hardcoded `2` with `config.MT5_RECONNECT_DELAY_BASE`. The loop does NOT sleep after the final failed attempt (no wasted wait before returning False):

```python
def connect_with_retry(retries: int = 3) -> bool:
    for attempt in range(retries):
        if connect():
            return True
        if attempt < retries - 1:
            wait = config.MT5_RECONNECT_DELAY_BASE ** (attempt + 1)
            logger.warning(f"MT5 connect attempt {attempt + 1} failed — retrying in {wait}s")
            time.sleep(wait)
        else:
            logger.warning(f"MT5 connect attempt {attempt + 1} failed — no more retries")
    return False
```

With defaults (`MT5_RECONNECT_RETRIES=3`, `MT5_RECONNECT_DELAY_BASE=2`): waits 2s then 4s between the 3 attempts — a maximum of 6 useful seconds before giving up.

**Also update `main()`**: the startup call must also use the configured value:
```python
if not connect_with_retry(config.MT5_RECONNECT_RETRIES):
    logger.critical("Cannot connect to MT5 after retries. Exiting.")
    return
```

---

## 5. Startup DRY_RUN Warning

In `main()`, after successful connect:

```python
if config.DRY_RUN:
    logger.warning("*** DRY_RUN MODE — orders will NOT be sent to MT5 ***")
```

---

## 6. Test Coverage

### 6a. `tests/test_mt5_connection.py` — 7 tests

All tests patch `src.mt5_bridge.connection.mt5` at the module level.

| Test | What it checks |
|---|---|
| `test_connect_success` | `mt5.initialize` returns True, `mt5.account_info()` returns mock with `.name` → `connect()` returns True |
| `test_connect_failure` | `mt5.initialize` returns False → `connect()` returns False, logs error |
| `test_disconnect_calls_shutdown` | `disconnect()` calls `mt5.shutdown()` once |
| `test_is_connected_true` | `mt5.account_info()` returns MagicMock → `is_connected()` is True |
| `test_is_connected_false` | `mt5.account_info()` returns None → `is_connected()` is False |
| `test_get_account_info_fields` | `mt5.account_info()` returns mock with balance=1000, equity=1010, currency="USD" → dict has all three correct keys/values |
| `test_connect_with_retry_uses_config_delay_base` | patch `config.MT5_RECONNECT_DELAY_BASE=3`, `connect()` fails twice then succeeds; assert `time.sleep` called with `3**1=3` then `3**2=9` |

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
| `test_place_order_dry_run` | `dry_run=True` → returns `{"success": True, "ticket": 0, "price": 0.0, "dry_run": True}` (all 4 keys asserted), `order_send` never called |
| `test_place_order_buy_success` | `order_send` returns mock with `retcode=mt5.TRADE_RETCODE_DONE`, `order=12345`, `price=1923.0` → `{"success": True, "ticket": 12345}` |
| `test_place_order_sell_success` | SELL uses `tick.bid` price; same success path |
| `test_place_order_rejected` | `order_send` returns mock with `retcode=10006`, `comment="rejected"` → `{"success": False, "retcode": 10006, "comment": "rejected"}` |
| `test_place_order_no_tick` | `symbol_info_tick` returns None → `{"success": False, "comment": "no tick data"}` |

### 6d. `tests/test_main.py` additions — 2 tests

Append to the existing `tests/test_main.py`:

| Test | What it checks |
|---|---|
| `test_reconnect_attempted_when_disconnected_and_candles_empty` | Patch `fetch_candles` → empty DataFrame, `is_connected` → False, `connect_with_retry` → True; assert `connect_with_retry` called and `_reconcile_missed_closes` called |
| `test_no_reconcile_when_reconnect_fails` | Patch `fetch_candles` → empty DataFrame, `is_connected` → False, `connect_with_retry` → False; assert `_reconcile_missed_closes` NOT called |

**Total new tests: 7 + 5 + 5 + 2 = 19. Expected final count: 116 + 19 = 135 passed.**

---

## 7. `.env.example` additions

Append the following block after the existing `# System` section in `.env.example`:

```
# Phase 4: Production mode
DRY_RUN=false
MT5_RECONNECT_RETRIES=3
MT5_RECONNECT_DELAY_BASE=2
```

---

## 8. Tag

After all 135 tests pass: `git tag v0.3.0-live`

---

## 9. Out of Scope for Phase 4

- Trade position monitoring / trailing stop (future phase)
- Telegram/email alerts on errors (future phase)
- Dashboard / web UI (future phase)
- Multiple symbols (XAUUSD only, by design)
