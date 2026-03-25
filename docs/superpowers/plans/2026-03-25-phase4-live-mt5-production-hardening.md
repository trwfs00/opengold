# Phase 4: Live MT5 + Production Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add DRY_RUN mode, in-loop MT5 reconnect with configurable backoff, and full unit-test coverage for the MT5 bridge and executor — reaching 135 tests and tagging v0.3.0-live.

**Architecture:** Three changes composited: (1) config gets 3 new env-vars; (2) `place_order` gets a `dry_run` param; (3) `connect_with_retry` and `run_loop` in `main.py` are updated for configurable backoff and mid-loop reconnect. All new tests mock the `MetaTrader5` package so they run without a live terminal.

**Tech Stack:** Python 3.12, MetaTrader5 (mocked in tests), pytest, unittest.mock

---

## File Map

| File | Action | What changes |
|---|---|---|
| `src/config.py` | Modify | Add `DRY_RUN`, `MT5_RECONNECT_RETRIES`, `MT5_RECONNECT_DELAY_BASE` |
| `.env.example` | Modify | Append Phase 4 env-vars after existing `# System` block |
| `src/executor/orders.py` | Modify | Add `dry_run: bool = False` param to `place_order` |
| `main.py` | Modify | Update `connect_with_retry` backoff, add in-loop reconnect, use config retries at startup, add DRY_RUN warning |
| `tests/test_mt5_connection.py` | Create | 7 tests for `src/mt5_bridge/connection.py` |
| `tests/test_mt5_data.py` | Create | 5 tests for `src/mt5_bridge/data.py` |
| `tests/test_executor_orders.py` | Create | 5 tests for `src/executor/orders.py` |
| `tests/test_main.py` | Modify | Append 2 tests for in-loop reconnect paths |

---

## Task 1: Config + .env.example

**Files:**
- Modify: `src/config.py` (after line 50, end of file)
- Modify: `.env.example` (after line 41, end of file)

- [ ] **Step 1: Add Phase 4 config vars to `src/config.py`**

Append after the last line (`DB_MAX_RETRY_DURATION_SECONDS = ...`):

```python

# Production mode
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
MT5_RECONNECT_RETRIES = int(os.getenv("MT5_RECONNECT_RETRIES", "3"))
MT5_RECONNECT_DELAY_BASE = int(os.getenv("MT5_RECONNECT_DELAY_BASE", "2"))
```

- [ ] **Step 2: Append Phase 4 vars to `.env.example`**

Append after the last line (`DB_MAX_RETRY_DURATION_SECONDS=3600`):

```
# Phase 4: Production mode
DRY_RUN=false
MT5_RECONNECT_RETRIES=3
MT5_RECONNECT_DELAY_BASE=2
```

- [ ] **Step 3: Verify config imports cleanly**

```
cd D:\hobbies\opengold
python -c "from src import config; print(config.DRY_RUN, config.MT5_RECONNECT_RETRIES, config.MT5_RECONNECT_DELAY_BASE)"
```

Expected output: `False 3 2`

- [ ] **Step 4: Run full suite to confirm no regressions**

```
python -m pytest tests/ --ignore=tests/integration -q
```

Expected: `116 passed`

- [ ] **Step 5: Commit**

```
git add src/config.py .env.example
git commit -m "feat: Phase 4 config - DRY_RUN, MT5_RECONNECT_RETRIES, MT5_RECONNECT_DELAY_BASE"
```

---

## Task 2: DRY_RUN in `place_order` + executor tests

**Files:**
- Modify: `src/executor/orders.py`
- Create: `tests/test_executor_orders.py`

### Step 1: Write the failing tests first

- [ ] **Step 1a: Create `tests/test_executor_orders.py`**

```python
# tests/test_executor_orders.py
from unittest.mock import MagicMock, patch, call


def _make_mt5_module():
    """Return a MagicMock that stands in for the MetaTrader5 module."""
    mt5 = MagicMock()
    mt5.ORDER_TYPE_BUY = 0
    mt5.ORDER_TYPE_SELL = 1
    mt5.TRADE_ACTION_DEAL = 1
    mt5.ORDER_TIME_GTC = 0
    mt5.ORDER_FILLING_IOC = 1
    mt5.TRADE_RETCODE_DONE = 10009
    return mt5


def test_place_order_dry_run():
    """dry_run=True returns success dict without calling order_send."""
    with patch("src.executor.orders.mt5", _make_mt5_module()) as mock_mt5:
        from src.executor.orders import place_order
        result = place_order("BUY", 0.01, 1918.0, 1945.0, dry_run=True)
    assert result == {"success": True, "ticket": 0, "price": 0.0, "dry_run": True}
    mock_mt5.order_send.assert_not_called()


def test_place_order_buy_success():
    """Successful BUY order returns ticket and price."""
    mock_mt5 = _make_mt5_module()
    tick = MagicMock()
    tick.ask = 1923.0
    mock_mt5.symbol_info_tick.return_value = tick
    order_result = MagicMock()
    order_result.retcode = mock_mt5.TRADE_RETCODE_DONE
    order_result.order = 12345
    order_result.price = 1923.0
    mock_mt5.order_send.return_value = order_result

    with patch("src.executor.orders.mt5", mock_mt5):
        from src.executor.orders import place_order
        result = place_order("BUY", 0.01, 1918.0, 1945.0)
    assert result["success"] is True
    assert result["ticket"] == 12345


def test_place_order_sell_success():
    """Successful SELL order uses bid price."""
    mock_mt5 = _make_mt5_module()
    tick = MagicMock()
    tick.bid = 1922.0
    mock_mt5.symbol_info_tick.return_value = tick
    order_result = MagicMock()
    order_result.retcode = mock_mt5.TRADE_RETCODE_DONE
    order_result.order = 99999
    order_result.price = 1922.0
    mock_mt5.order_send.return_value = order_result

    with patch("src.executor.orders.mt5", mock_mt5):
        from src.executor.orders import place_order
        result = place_order("SELL", 0.01, 1940.0, 1910.0)
    assert result["success"] is True
    assert result["ticket"] == 99999


def test_place_order_rejected():
    """Rejected order returns success=False with retcode and comment."""
    mock_mt5 = _make_mt5_module()
    tick = MagicMock()
    tick.ask = 1923.0
    mock_mt5.symbol_info_tick.return_value = tick
    order_result = MagicMock()
    order_result.retcode = 10006
    order_result.comment = "rejected"
    mock_mt5.order_send.return_value = order_result

    with patch("src.executor.orders.mt5", mock_mt5):
        from src.executor.orders import place_order
        result = place_order("BUY", 0.01, 1918.0, 1945.0)
    assert result["success"] is False
    assert result["retcode"] == 10006
    assert result["comment"] == "rejected"


def test_place_order_no_tick():
    """No tick data returns success=False with descriptive comment."""
    mock_mt5 = _make_mt5_module()
    mock_mt5.symbol_info_tick.return_value = None

    with patch("src.executor.orders.mt5", mock_mt5):
        from src.executor.orders import place_order
        result = place_order("BUY", 0.01, 1918.0, 1945.0)
    assert result["success"] is False
    assert result["comment"] == "no tick data"
```

- [ ] **Step 1b: Run to confirm RED**

```
python -m pytest tests/test_executor_orders.py -v
```

Expected: `TypeError` or `ImportError` on `dry_run` parameter (test_place_order_dry_run fails, others may pass or fail on kwargs)

- [ ] **Step 2: Add `dry_run` parameter to `place_order` in `src/executor/orders.py`**

Change the function signature from:
```python
def place_order(direction: str, lot_size: float, sl: float, tp: float) -> dict:
    """Place a market order. Returns dict with success bool and ticket/error."""
    order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
```

To:
```python
def place_order(direction: str, lot_size: float, sl: float, tp: float, dry_run: bool = False) -> dict:
    """Place a market order. Returns dict with success bool and ticket/error."""
    if dry_run:
        logger.info(f"DRY_RUN order: {direction} {lot_size} lots sl={sl} tp={tp}")
        return {"success": True, "ticket": 0, "price": 0.0, "dry_run": True}
    order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
```

- [ ] **Step 3: Run executor tests — confirm GREEN**

```
python -m pytest tests/test_executor_orders.py -v
```

Expected: `5 passed`

- [ ] **Step 4: Run full suite**

```
python -m pytest tests/ --ignore=tests/integration -q
```

Expected: `121 passed` (116 + 5)

- [ ] **Step 5: Commit**

```
git add src/executor/orders.py tests/test_executor_orders.py
git commit -m "feat: place_order dry_run mode + executor unit tests"
```

---

## Task 3: MT5 connection tests

**Files:**
- Modify: `main.py` (update `connect_with_retry` backoff to use config)
- Create: `tests/test_mt5_connection.py`

Note: `connect_with_retry` lives in `main.py`. Its configurable-backoff production change must happen **before** the test file is created — `test_connect_with_retry_uses_config_delay_base` directly tests that behavior.

- [ ] **Step 1: Update `connect_with_retry` in `main.py` to use `config.MT5_RECONNECT_DELAY_BASE`**

Find this existing function:

```python
def connect_with_retry(retries: int = 3) -> bool:
    for attempt in range(retries):
        if connect():
            return True
        wait = 2 ** (attempt + 1)   # 2s, 4s, 8s
        logger.warning(f"MT5 connect attempt {attempt + 1} failed — retrying in {wait}s")
        time.sleep(wait)
    return False
```

Replace with:

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

- [ ] **Step 2: Create `tests/test_mt5_connection.py`**

```python
# tests/test_mt5_connection.py
from unittest.mock import MagicMock, patch, call


def test_connect_success():
    """connect() returns True when mt5.initialize succeeds."""
    mock_mt5 = MagicMock()
    mock_mt5.initialize.return_value = True
    mock_mt5.account_info.return_value = MagicMock(name="TestAccount")
    with patch("src.mt5_bridge.connection.mt5", mock_mt5):
        from src.mt5_bridge.connection import connect
        result = connect()
    assert result is True


def test_connect_failure():
    """connect() returns False when mt5.initialize fails."""
    mock_mt5 = MagicMock()
    mock_mt5.initialize.return_value = False
    mock_mt5.last_error.return_value = (1, "auth error")
    with patch("src.mt5_bridge.connection.mt5", mock_mt5):
        from src.mt5_bridge.connection import connect
        result = connect()
    assert result is False


def test_disconnect_calls_shutdown():
    """disconnect() calls mt5.shutdown() exactly once."""
    mock_mt5 = MagicMock()
    with patch("src.mt5_bridge.connection.mt5", mock_mt5):
        from src.mt5_bridge.connection import disconnect
        disconnect()
    mock_mt5.shutdown.assert_called_once()


def test_is_connected_true():
    """is_connected() returns True when account_info is not None."""
    mock_mt5 = MagicMock()
    mock_mt5.account_info.return_value = MagicMock()
    with patch("src.mt5_bridge.connection.mt5", mock_mt5):
        from src.mt5_bridge.connection import is_connected
        assert is_connected() is True


def test_is_connected_false():
    """is_connected() returns False when account_info returns None."""
    mock_mt5 = MagicMock()
    mock_mt5.account_info.return_value = None
    with patch("src.mt5_bridge.connection.mt5", mock_mt5):
        from src.mt5_bridge.connection import is_connected
        assert is_connected() is False


def test_get_account_info_fields():
    """get_account_info() returns dict with balance, equity, currency."""
    mock_mt5 = MagicMock()
    info = MagicMock()
    info.balance = 1000.0
    info.equity = 1010.0
    info.currency = "USD"
    mock_mt5.account_info.return_value = info
    with patch("src.mt5_bridge.connection.mt5", mock_mt5):
        from src.mt5_bridge.connection import get_account_info
        result = get_account_info()
    assert result == {"balance": 1000.0, "equity": 1010.0, "currency": "USD"}


def test_connect_with_retry_uses_config_delay_base():
    """connect_with_retry sleeps with config.MT5_RECONNECT_DELAY_BASE exponent."""
    # connect() fails first two attempts, succeeds on third
    connect_results = [False, False, True]
    with (
        patch("main.connect", side_effect=connect_results),
        patch("main.config") as mock_config,
        patch("main.time") as mock_time,
    ):
        mock_config.MT5_RECONNECT_DELAY_BASE = 3
        from main import connect_with_retry
        result = connect_with_retry(retries=3)

    assert result is True
    # First failure: sleep(3^1=3), second failure: sleep(3^2=9), no sleep after success
    assert mock_time.sleep.call_args_list == [call(3), call(9)]
```

- [ ] **Step 3: Run to confirm all 7 pass**

```
python -m pytest tests/test_mt5_connection.py -v
```

Expected: `7 passed`

- [ ] **Step 4: Run full suite**

```
python -m pytest tests/ --ignore=tests/integration -q
```

Expected: `128 passed` (121 + 7)

- [ ] **Step 5: Commit**

```
git add main.py tests/test_mt5_connection.py
git commit -m "feat: connect_with_retry configurable backoff + MT5 connection tests (7 tests, mocked)"
```

---

## Task 4: MT5 data tests

**Files:**
- Create: `tests/test_mt5_data.py`
- No production code changes in this task

- [ ] **Step 1: Create `tests/test_mt5_data.py`**

```python
# tests/test_mt5_data.py
from unittest.mock import MagicMock, patch
import numpy as np
from datetime import datetime, timezone


def _make_rate(ts=1700000000):
    """Return a numpy-style struct-like object representing one OHLCV candle."""
    rate = MagicMock()
    rate.__getitem__ = lambda self, k: {
        "time": ts, "open": 1920.0, "high": 1925.0,
        "low": 1915.0, "close": 1922.0, "tick_volume": 1000,
    }[k]
    return rate


def test_fetch_candles_returns_dataframe():
    """fetch_candles returns DataFrame with expected columns."""
    import pandas as pd

    dt = np.dtype([
        ("time", np.int64), ("open", np.float64), ("high", np.float64),
        ("low", np.float64), ("close", np.float64), ("tick_volume", np.int64),
    ])
    rates = np.array([(1700000000, 1920.0, 1925.0, 1915.0, 1922.0, 1000)], dtype=dt)

    mock_mt5 = MagicMock()
    mock_mt5.copy_rates_from_pos.return_value = rates
    mock_mt5.TIMEFRAME_M1 = 1

    with patch("src.mt5_bridge.data.mt5", mock_mt5):
        from src.mt5_bridge.data import fetch_candles
        df = fetch_candles(count=1)

    assert list(df.columns) == ["time", "open", "high", "low", "close", "volume"]
    assert len(df) == 1


def test_fetch_candles_empty_on_none():
    """fetch_candles returns empty DataFrame when mt5 returns None."""
    mock_mt5 = MagicMock()
    mock_mt5.copy_rates_from_pos.return_value = None
    mock_mt5.TIMEFRAME_M1 = 1
    mock_mt5.last_error.return_value = (1, "error")

    with patch("src.mt5_bridge.data.mt5", mock_mt5):
        from src.mt5_bridge.data import fetch_candles
        df = fetch_candles()

    assert df.empty


def test_get_last_candle_time_returns_datetime():
    """get_last_candle_time returns a timezone-aware datetime."""
    dt = np.dtype([("time", np.int64)])
    rates = np.array([(1700000000,)], dtype=dt)

    mock_mt5 = MagicMock()
    mock_mt5.copy_rates_from_pos.return_value = rates
    mock_mt5.TIMEFRAME_M1 = 1

    with patch("src.mt5_bridge.data.mt5", mock_mt5):
        from src.mt5_bridge.data import get_last_candle_time
        result = get_last_candle_time()

    assert isinstance(result, datetime)
    assert result.tzinfo is not None


def test_get_positions_returns_list():
    """get_positions returns list of dicts with expected keys."""
    pos = MagicMock()
    pos.ticket = 111
    pos.type = 0  # ORDER_TYPE_BUY
    pos.volume = 0.01
    pos.price_open = 1920.0
    pos.sl = 1910.0
    pos.tp = 1940.0

    mock_mt5 = MagicMock()
    mock_mt5.ORDER_TYPE_BUY = 0
    mock_mt5.positions_get.return_value = [pos]
    mock_mt5.TIMEFRAME_M1 = 1

    with patch("src.mt5_bridge.data.mt5", mock_mt5):
        from src.mt5_bridge.data import get_positions
        result = get_positions()

    assert len(result) == 1
    assert result[0]["direction"] == "BUY"
    assert result[0]["ticket"] == 111


def test_get_history_deals_filters_symbol():
    """get_history_deals filters out deals whose symbol != XAUUSD."""
    from datetime import datetime, timezone

    good_deal = MagicMock()
    good_deal.ticket = 1
    good_deal.order = 10
    good_deal.time = 1700000000
    good_deal.type = 1
    good_deal.volume = 0.01
    good_deal.price = 1920.0
    good_deal.profit = 42.0
    good_deal.symbol = "XAUUSD"
    good_deal.entry = 1

    bad_deal = MagicMock()
    bad_deal.symbol = "EURUSD"
    bad_deal.entry = 1

    mock_mt5 = MagicMock()
    mock_mt5.history_deals_get.return_value = [good_deal, bad_deal]
    mock_mt5.TIMEFRAME_M1 = 1

    with patch("src.mt5_bridge.data.mt5", mock_mt5):
        from src.mt5_bridge.data import get_history_deals
        now = datetime.now(timezone.utc)
        result = get_history_deals(now, now)

    assert len(result) == 1
    assert result[0]["ticket"] == 1
```

- [ ] **Step 2: Run to confirm all 5 pass**

```
python -m pytest tests/test_mt5_data.py -v
```

Expected: `5 passed`

- [ ] **Step 3: Run full suite**

```
python -m pytest tests/ --ignore=tests/integration -q
```

Expected: `133 passed` (128 + 5)

- [ ] **Step 4: Commit**

```
git add tests/test_mt5_data.py
git commit -m "test: MT5 data unit tests (5 tests, mocked)"
```

---

## Task 5: Update `main.py` + add reconnect tests

**Files:**
- Modify: `main.py`
- Modify: `tests/test_main.py` (append 2 tests)

### Part A: Production code changes

- [ ] **Step 1: Update `main()` startup call to use `config.MT5_RECONNECT_RETRIES`**

Note: `connect_with_retry` itself was already updated in Task 3 Step 1. Only the call site needs to change here.

Find:
```python
    if not connect_with_retry():
        logger.critical("Cannot connect to MT5 after retries. Exiting.")
        return
```

Replace with:
```python
    if not connect_with_retry(config.MT5_RECONNECT_RETRIES):
        logger.critical("Cannot connect to MT5 after retries. Exiting.")
        return
```

- [ ] **Step 2: Add DRY_RUN warning in `main()` after successful connect**

Find (in the `main()` function, after the failed-connect early return):
```python
    run_loop()
```

Replace with:
```python
    if config.DRY_RUN:
        logger.warning("*** DRY_RUN MODE — orders will NOT be sent to MT5 ***")
    run_loop()
```

- [ ] **Step 3: Add in-loop reconnect to `run_loop()` in `main.py`**

Find the existing empty-candles early-exit block:
```python
            if candles.empty:
                time.sleep(config.POLL_INTERVAL_SECONDS)
                continue
```

Replace with:
```python
            if candles.empty:
                if not is_connected():
                    logger.warning("MT5 connection lost — attempting reconnect")
                    if connect_with_retry(config.MT5_RECONNECT_RETRIES):
                        logger.info("Reconnected — reconciling missed closes")
                        _reconcile_missed_closes()
                    else:
                        logger.error("Reconnect failed — will retry next candle")
                # If is_connected() is True but candles are still empty (market closed,
                # weekend, holiday), the reconnect block is skipped — intentional.
                time.sleep(config.POLL_INTERVAL_SECONDS)
                continue
```

- [ ] **Step 4: Update `place_order` call in `run_loop()` to pass `dry_run`**

Find:
```python
            order = place_order(direction, risk.lot_size, sl, tp)
```

Replace with:
```python
            order = place_order(direction, risk.lot_size, sl, tp, dry_run=config.DRY_RUN)
```

- [ ] **Step 5: Run full suite — confirm still 133 passed (no regressions)**

```
python -m pytest tests/ --ignore=tests/integration -q
```

Expected: `133 passed`

### Part B: Reconnect tests

- [ ] **Step 6: Append 2 reconnect tests to `tests/test_main.py`**

Append at the end of `tests/test_main.py`:

```python
def test_reconnect_attempted_when_disconnected_and_candles_empty():
    """When candles empty and MT5 disconnected, connect_with_retry and reconcile are called."""
    from main import run_loop
    import pandas as pd
    with (
        patch("main.fetch_candles", return_value=pd.DataFrame()),
        patch("main.is_connected", return_value=False),
        patch("main.connect_with_retry", return_value=True) as mock_retry,
        patch("main._reconcile_missed_closes") as mock_reconcile,
        patch("main.time") as mock_time,
    ):
        mock_time.sleep.side_effect = StopIteration
        try:
            run_loop()
        except StopIteration:
            pass

    mock_retry.assert_called_once()
    mock_reconcile.assert_called_once()


def test_no_reconcile_when_reconnect_fails():
    """When reconnect fails, _reconcile_missed_closes is NOT called."""
    from main import run_loop
    import pandas as pd
    with (
        patch("main.fetch_candles", return_value=pd.DataFrame()),
        patch("main.is_connected", return_value=False),
        patch("main.connect_with_retry", return_value=False),
        patch("main._reconcile_missed_closes") as mock_reconcile,
        patch("main.time") as mock_time,
    ):
        mock_time.sleep.side_effect = StopIteration
        try:
            run_loop()
        except StopIteration:
            pass

    mock_reconcile.assert_not_called()
```

- [ ] **Step 7: Run all tests — confirm 135 passed**

```
python -m pytest tests/ --ignore=tests/integration -q
```

Expected: `135 passed`

- [ ] **Step 8: Commit**

```
git add main.py tests/test_main.py
git commit -m "feat: in-loop MT5 reconnect startup wired to config, DRY_RUN wired to place_order"
```

---

## Task 6: Tag v0.3.0-live

- [ ] **Step 1: Final full suite run**

```
python -m pytest tests/ --ignore=tests/integration -q
```

Expected output must include: `135 passed`

- [ ] **Step 2: Tag**

```
git tag v0.3.0-live
git log --oneline -5
```

Expected: `v0.3.0-live` tag appears on the latest commit.

- [ ] **Step 3: Verify `.env` has `DRY_RUN` and `ANTHROPIC_API_KEY`**

```
python -c "from src import config; print('DRY_RUN:', config.DRY_RUN); print('retries:', config.MT5_RECONNECT_RETRIES)"
```

Expected: reflects your `.env` values.

---

## Acceptance Criteria

- [ ] `python -m pytest tests/ --ignore=tests/integration -q` → `135 passed`
- [ ] `git tag` shows `v0.3.0-live`
- [ ] `DRY_RUN=false` in `.env.example`
- [ ] `place_order` with `dry_run=True` logs a message and returns `{"success": True, "ticket": 0, "price": 0.0, "dry_run": True}` without calling `mt5.order_send`
- [ ] `connect_with_retry` does NOT sleep after the final failed attempt
