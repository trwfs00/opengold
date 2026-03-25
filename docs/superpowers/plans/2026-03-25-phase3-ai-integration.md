# Phase 3 — AI Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Claude Haiku (with Sonnet fallback) into the trading loop — journal context fetcher, prompt builder, AI client, and updated `main.py` that replaces the Phase 1 fixed-confidence placeholder with real AI decisions.

**Architecture:** Three new modules (`journal`, `ai_layer`, `ai_layer/prompt`) plus a thin update to `main.py`. The journal fetches the last N closed trades from TimescaleDB and serialises them to a compact text block. The prompt module combines journal + market state into a structured prompt. The AI client sends the prompt to Claude Haiku, falls back to Sonnet on error, and returns a typed `AIDecision` dataclass. `main.py` calls these in sequence after the trigger fires.

**Tech Stack:** Python 3.12, `anthropic>=0.21.0` (already in requirements.txt), `psycopg2` via existing `src/db.py`, `src/config.py` for `ANTHROPIC_API_KEY` / `JOURNAL_TRADE_COUNT`.

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `src/journal/__init__.py` | Create | Empty package marker |
| `src/journal/reader.py` | Create | `get_journal_context(n) -> str` — reads trades table, serialises to compact text |
| `src/ai_layer/__init__.py` | Create | Empty package marker |
| `src/ai_layer/prompt.py` | Create | `build_prompt(journal, regime, buy_score, sell_score, price, atr) -> str` |
| `src/ai_layer/client.py` | Create | `decide(prompt: str) -> AIDecision` — Haiku → Sonnet fallback, JSON parse |
| `src/config.py` | Modify | Add `ANTHROPIC_API_KEY`, `CLAUDE_PRIMARY_MODEL`, `CLAUDE_FALLBACK_MODEL` |
| `main.py` | Modify | Replace fixed-confidence block with `journal → prompt → decide → risk → execute` |
| `tests/test_journal.py` | Create | Unit tests for `get_journal_context` |
| `tests/test_ai_prompt.py` | Create | Unit tests for `build_prompt` |
| `tests/test_ai_client.py` | Create | Unit tests for `decide` (mocked Anthropic client) |

---

## Task 1: Journal Reader

**Files:**
- Create: `src/journal/__init__.py`
- Create: `src/journal/reader.py`
- Test: `tests/test_journal.py`

- [ ] **Step 1.1: Write the failing tests**

```python
# tests/test_journal.py
from unittest.mock import patch
from src.journal.reader import get_journal_context


def test_returns_string():
    """get_journal_context always returns a str."""
    with patch("src.journal.reader.execute", return_value=[]):
        result = get_journal_context(n=10)
    assert isinstance(result, str)


def test_empty_trades_returns_empty_string():
    """With no trades, returns empty string (prompt skips journal section)."""
    with patch("src.journal.reader.execute", return_value=[]):
        result = get_journal_context(n=10)
    assert result == ""


def test_formats_single_trade():
    """A single BUY WIN trade is serialised in the expected format."""
    rows = [
        # (open_time, direction, regime, buy_score, sell_score, pnl, result, sl, tp)
        ("2026-03-25 10:00:00", "BUY", "TRENDING", 7.1, 1.2, 42.0, "WIN", 1920.0, 1940.0),
    ]
    with patch("src.journal.reader.execute", return_value=rows):
        result = get_journal_context(n=10)
    assert "[1] BUY" in result
    assert "TRENDING" in result
    assert "+$42" in result
    assert "WIN" in result


def test_formats_loss_trade():
    """A LOSS trade renders sign before the dollar sign: -$18, not $-18."""
    rows = [
        ("2026-03-25 11:00:00", "SELL", "RANGING", 1.1, 6.4, -18.0, "LOSS", 1935.0, 1918.0),
    ]
    with patch("src.journal.reader.execute", return_value=rows):
        result = get_journal_context(n=10)
    assert "-$18" in result
    assert "$-18" not in result


def test_null_scores_dont_crash():
    """NULL buy_score/sell_score from LEFT JOIN (no matching decision) must not crash."""
    rows = [
        ("2026-03-25 10:00:00", "BUY", None, None, None, 42.0, "WIN", 1920.0, 1940.0),
    ]
    with patch("src.journal.reader.execute", return_value=rows):
        result = get_journal_context(n=10)   # must not raise TypeError
    assert isinstance(result, str)


def test_summary_line_present_with_trades():
    """Summary line (Win rate / Avg win / Avg loss / Net) is included when trades exist."""
    rows = [
        ("2026-03-25 10:00:00", "BUY", "TRENDING", 7.1, 1.2, 42.0, "WIN", 1920.0, 1940.0),
        ("2026-03-25 11:00:00", "SELL", "RANGING", 1.1, 6.4, -18.0, "LOSS", 1935.0, 1918.0),
    ]
    with patch("src.journal.reader.execute", return_value=rows):
        result = get_journal_context(n=10)
    assert "Win rate:" in result
    assert "Net:" in result


def test_respects_n_limit():
    """Query is called with the correct LIMIT."""
    with patch("src.journal.reader.execute", return_value=[]) as mock_exec:
        get_journal_context(n=5)
    assert mock_exec.call_args.args[1] == (5,)
```

- [ ] **Step 1.2: Run to confirm RED**

```
cd D:\hobbies\opengold
python -m pytest tests/test_journal.py -v
```
Expected: `ModuleNotFoundError: No module named 'src.journal'`

> Note: there are now **7 tests** in `test_journal.py` (added `test_formats_loss_trade` and `test_null_scores_dont_crash`).

- [ ] **Step 1.3: Create empty package**

```python
# src/journal/__init__.py
# (empty)
```

- [ ] **Step 1.4: Implement `src/journal/reader.py`**

```python
import logging
from src.db import execute
from src import config

logger = logging.getLogger(__name__)

_QUERY = """
    SELECT
        t.open_time, t.direction, d.regime,
        d.buy_score, d.sell_score,
        t.pnl, t.result, t.sl, t.tp
    FROM trades t
    LEFT JOIN LATERAL (
        SELECT regime, buy_score, sell_score
        FROM decisions
        WHERE time <= t.open_time
        ORDER BY time DESC
        LIMIT 1
    ) d ON TRUE
    ORDER BY t.open_time DESC
    LIMIT %s
"""


def get_journal_context(n: int | None = None) -> str:
    """Fetch the last n closed trades and return a compact journal string.

    Returns an empty string if no trades exist (caller omits the journal section).
    n defaults to config.JOURNAL_TRADE_COUNT.
    """
    if n is None:
        n = config.JOURNAL_TRADE_COUNT
    try:
        rows = execute(_QUERY, (n,), fetch=True) or []
    except Exception as e:
        logger.error(f"journal fetch failed: {e}")
        return ""

    if not rows:
        return ""

    lines = []
    wins = 0
    total_win_pnl = 0.0
    total_loss_pnl = 0.0

    for i, row in enumerate(rows, 1):
        _, direction, regime, buy_score, sell_score, pnl, result, sl, tp = row
        buy_score = buy_score or 0.0   # guard NULL from LEFT JOIN
        sell_score = sell_score or 0.0
        regime_str = regime or "UNKNOWN"
        result_str = result or "UNKNOWN"
        sign = "+" if pnl >= 0 else "-"          # sign BEFORE dollar sign
        pnl_str = f"{sign}${abs(pnl):.0f}"
        lines.append(
            f"[{i}] {direction:<4} {regime_str:<8} "
            f"buy={buy_score:.1f} sell={sell_score:.1f} "
            f"→ {result_str:<8} {pnl_str:<8} "
            f"(SL={sl} TP={tp})"
        )
        if result == "WIN":
            wins += 1
            total_win_pnl += pnl
        elif result == "LOSS":
            total_loss_pnl += abs(pnl)

    total = len(rows)
    avg_win = total_win_pnl / wins if wins else 0.0
    losses = total - wins
    avg_loss = total_loss_pnl / losses if losses else 0.0
    net = sum(r[5] for r in rows)

    summary = (
        f"Win rate: {wins}/{total} | "
        f"Avg win: ${avg_win:.0f} | "
        f"Avg loss: ${avg_loss:.0f} | "
        f"Net: {'+' if net >= 0 else ''}${net:.0f}"
    )
    header = f"RECENT TRADES (last {total}):"
    return "\n".join([header] + lines + [summary])
```

- [ ] **Step 1.5: Run tests — confirm GREEN**

```
python -m pytest tests/test_journal.py -v
```
Expected: 7 passed

- [ ] **Step 1.6: Run full suite — confirm no regressions**

```
python -m pytest tests/ --ignore=tests/integration -q
```
Expected: 102 passed (95 + 7 new)

- [ ] **Step 1.7: Commit**

```bash
git add src/journal/__init__.py src/journal/reader.py tests/test_journal.py
git commit -m "feat: journal reader - compact trade history for AI context"
```

---

## Task 2: Prompt Builder

**Files:**
- Create: `src/ai_layer/__init__.py`
- Create: `src/ai_layer/prompt.py`
- Test: `tests/test_ai_prompt.py`

- [ ] **Step 2.1: Write the failing tests**

```python
# tests/test_ai_prompt.py
from src.ai_layer.prompt import build_prompt


def test_returns_string():
    result = build_prompt(
        journal="",
        regime="TRENDING",
        buy_score=7.2,
        sell_score=1.1,
        price=1923.45,
        atr=3.2,
    )
    assert isinstance(result, str)


def test_contains_regime():
    result = build_prompt(
        journal="", regime="RANGING", buy_score=5.5, sell_score=5.0,
        price=1900.0, atr=2.0,
    )
    assert "RANGING" in result


def test_contains_price_and_atr():
    result = build_prompt(
        journal="", regime="TRENDING", buy_score=7.0, sell_score=1.0,
        price=1923.45, atr=3.2,
    )
    assert "1923.45" in result
    assert "3.2" in result


def test_journal_section_included_when_present():
    journal = "RECENT TRADES (last 1):\n[1] BUY TRENDING ..."
    result = build_prompt(
        journal=journal, regime="TRENDING", buy_score=7.0, sell_score=1.0,
        price=1923.45, atr=3.2,
    )
    assert "[JOURNAL]" in result
    assert "RECENT TRADES" in result


def test_journal_section_omitted_when_empty():
    result = build_prompt(
        journal="", regime="TRENDING", buy_score=7.0, sell_score=1.0,
        price=1923.45, atr=3.2,
    )
    assert "[JOURNAL]" not in result


def test_task_section_present():
    result = build_prompt(
        journal="", regime="TRENDING", buy_score=7.0, sell_score=1.0,
        price=1923.45, atr=3.2,
    )
    assert "[TASK]" in result
    assert "BUY" in result
    assert "SELL" in result
    assert "SKIP" in result
    assert "JSON" in result
```

- [ ] **Step 2.2: Run to confirm RED**

```
python -m pytest tests/test_ai_prompt.py -v
```
Expected: `ModuleNotFoundError: No module named 'src.ai_layer'`

- [ ] **Step 2.3: Create empty package**

```python
# src/ai_layer/__init__.py
# (empty)
```

- [ ] **Step 2.4: Implement `src/ai_layer/prompt.py`**

```python
def build_prompt(
    journal: str,
    regime: str,
    buy_score: float,
    sell_score: float,
    price: float,
    atr: float,
) -> str:
    """Build the structured prompt to send to Claude.

    Journal section is omitted when journal is empty string.
    """
    parts = []

    if journal:
        parts.append(f"[JOURNAL]\n{journal}")

    parts.append(
        f"[MARKET]\n"
        f"Regime: {regime} | buy_score: {buy_score:.1f} | sell_score: {sell_score:.1f}\n"
        f"Price: {price} | ATR: {atr:.2f}"
    )

    parts.append(
        "[TASK]\n"
        "Decide: BUY, SELL, or SKIP. If BUY or SELL, provide SL and TP in price.\n"
        'Reply in JSON only: {"action":"BUY","confidence":0.85,"sl":1918.0,"tp":1938.0}'
    )

    return "\n\n".join(parts)
```

- [ ] **Step 2.5: Run tests — confirm GREEN**

```
python -m pytest tests/test_ai_prompt.py -v
```
Expected: 7 passed

- [ ] **Step 2.6: Run full suite**

```
python -m pytest tests/ --ignore=tests/integration -q
```
Expected: 109 passed (102 + 7 new)

- [ ] **Step 2.7: Commit**

```bash
git add src/ai_layer/__init__.py src/ai_layer/prompt.py tests/test_ai_prompt.py
git commit -m "feat: AI prompt builder with journal + market context"
```

---

## Task 3: AI Client

**Files:**
- Create: `src/ai_layer/client.py`
- Modify: `src/config.py` (add 3 keys)
- Test: `tests/test_ai_client.py`

- [ ] **Step 3.1: Add config keys to `src/config.py`**

Add after the existing `DB_PASSWORD` block:

```python
# Claude AI
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
# Use full versioned model IDs — check https://docs.anthropic.com/en/docs/about-claude/models
# for the latest available names. Defaults: Claude 3.5 Haiku / 3.5 Sonnet (stable as of early 2026).
CLAUDE_PRIMARY_MODEL = os.getenv("CLAUDE_PRIMARY_MODEL", "claude-3-5-haiku-20241022")
CLAUDE_FALLBACK_MODEL = os.getenv("CLAUDE_FALLBACK_MODEL", "claude-3-5-sonnet-20241022")

if not ANTHROPIC_API_KEY:
    import logging as _logging
    _logging.getLogger(__name__).warning("ANTHROPIC_API_KEY not set — AI calls will fail at runtime")
```

- [ ] **Step 3.2: Write the failing tests**

```python
# tests/test_ai_client.py
from dataclasses import dataclass
from unittest.mock import MagicMock, patch
import pytest
from src.ai_layer.client import decide, AIDecision


def _mock_response(json_text: str):
    """Build a minimal mock that mimics anthropic.types.Message structure."""
    content_block = MagicMock()
    content_block.text = json_text
    msg = MagicMock()
    msg.content = [content_block]
    return msg


def test_returns_ai_decision():
    resp = _mock_response('{"action":"BUY","confidence":0.85,"sl":1918.0,"tp":1938.0}')
    with patch("src.ai_layer.client.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = resp
        result = decide("test prompt")
    assert isinstance(result, AIDecision)


def test_buy_action_parsed():
    resp = _mock_response('{"action":"BUY","confidence":0.85,"sl":1918.0,"tp":1938.0}')
    with patch("src.ai_layer.client.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = resp
        result = decide("test prompt")
    assert result.action == "BUY"
    assert result.confidence == pytest.approx(0.85)
    assert result.sl == pytest.approx(1918.0)
    assert result.tp == pytest.approx(1938.0)
    assert result.error is None


def test_skip_action():
    resp = _mock_response('{"action":"SKIP","confidence":0.0,"sl":0.0,"tp":0.0}')
    with patch("src.ai_layer.client.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = resp
        result = decide("test prompt")
    assert result.action == "SKIP"


def test_malformed_json_returns_skip_with_error():
    """Non-JSON response → SKIP, error='AI_PARSE_ERROR'."""
    resp = _mock_response("sorry, I cannot decide right now")
    with patch("src.ai_layer.client.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = resp
        result = decide("test prompt")
    assert result.action == "SKIP"
    assert result.error == "AI_PARSE_ERROR"


def test_haiku_failure_falls_back_to_sonnet():
    """First call (Haiku) raises exception → second call (Sonnet) succeeds."""
    resp = _mock_response('{"action":"SELL","confidence":0.7,"sl":1930.0,"tp":1910.0}')
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [Exception("timeout"), resp]
    with patch("src.ai_layer.client.anthropic.Anthropic", return_value=mock_client):
        result = decide("test prompt")
    assert result.action == "SELL"
    assert mock_client.messages.create.call_count == 2


def test_both_models_fail_returns_skip():
    """Both Haiku and Sonnet fail → SKIP, error='AI_API_ERROR'."""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("network error")
    with patch("src.ai_layer.client.anthropic.Anthropic", return_value=mock_client):
        result = decide("test prompt")
    assert result.action == "SKIP"
    assert result.error == "AI_API_ERROR"
```

- [ ] **Step 3.3: Run to confirm RED**

```
python -m pytest tests/test_ai_client.py -v
```
Expected: `ModuleNotFoundError: No module named 'src.ai_layer.client'`

- [ ] **Step 3.4: Implement `src/ai_layer/client.py`**

```python
import json
import logging
from dataclasses import dataclass, field

import anthropic

from src import config

logger = logging.getLogger(__name__)


@dataclass
class AIDecision:
    action: str          # "BUY" | "SELL" | "SKIP"
    confidence: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    error: str | None = None


def _call_model(client: anthropic.Anthropic, model: str, prompt: str) -> str:
    """Send prompt to model and return raw text response."""
    msg = client.messages.create(
        model=model,
        max_tokens=128,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def _parse(raw: str) -> AIDecision:
    """Parse Claude JSON response into AIDecision. Returns SKIP on failure."""
    try:
        # Extract JSON — Claude sometimes wraps in markdown fences
        text = raw.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text)
        action = str(data.get("action", "SKIP")).upper()
        if action not in {"BUY", "SELL", "SKIP"}:
            action = "SKIP"
        return AIDecision(
            action=action,
            confidence=float(data.get("confidence", 0.0)),
            sl=float(data.get("sl", 0.0)),
            tp=float(data.get("tp", 0.0)),
        )
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        logger.warning(f"AI_PARSE_ERROR: could not parse response: {raw!r}")
        return AIDecision(action="SKIP", error="AI_PARSE_ERROR")


def decide(prompt: str) -> AIDecision:
    """Send prompt to Claude Haiku; fall back to Sonnet on error.

    Returns AIDecision(action='SKIP', error='AI_API_ERROR') if both models fail.
    Never raises.
    """
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    for model in (config.CLAUDE_PRIMARY_MODEL, config.CLAUDE_FALLBACK_MODEL):
        try:
            raw = _call_model(client, model, prompt)
            logger.info(f"AI response ({model}): {raw!r}")
            return _parse(raw)
        except Exception as e:
            logger.warning(f"AI model {model} failed: {e}")

    return AIDecision(action="SKIP", error="AI_API_ERROR")
```

- [ ] **Step 3.5: Run tests — confirm GREEN**

```
python -m pytest tests/test_ai_client.py -v
```
Expected: 6 passed

- [ ] **Step 3.6: Run full suite**

```
python -m pytest tests/ --ignore=tests/integration -q
```
Expected: 115 passed (109 + 6 new)

- [ ] **Step 3.7: Commit**

```bash
git add src/ai_layer/client.py src/config.py tests/test_ai_client.py
git commit -m "feat: Claude Haiku/Sonnet AI client with JSON parsing and fallback"
```

---

## Task 4: Wire AI into `main.py`

**Files:**
- Modify: `main.py` (replace Phase 1 fixed-confidence block)
- Modify: `tests/test_main.py` (add smoke test for the updated flow)

The current `main.py` has this placeholder block after the trigger fires (starting approximately at the comment `# ── Phase 1: direction from scores, fixed confidence, ATR-based SL/TP ──`):

```python
# ── Phase 1: direction from scores, fixed confidence, ATR-based SL/TP ──
direction = get_direction(agg)
price = candles["close"].iloc[-1]
atr_range = (
    candles["high"].rolling(14).max() - candles["low"].rolling(14).min()
).iloc[-1]
if direction == "BUY":
    sl = price - atr_range * 1.5
    tp = price + atr_range * 2.0
else:
    sl = price + atr_range * 1.5
    tp = price - atr_range * 2.0
confidence = 0.75   # fixed in Phase 1; replaced by AI confidence in Phase 3
```

Replace it with AI pipeline:

```python
# ── Phase 3: journal → AI → risk ─────────────────────────────────────
price = candles["close"].iloc[-1]
atr = (
    candles["high"].rolling(14).max() - candles["low"].rolling(14).min()
).iloc[-1]
journal = get_journal_context()
ai_prompt = build_prompt(
    journal=journal,
    regime=regime,
    buy_score=agg.buy_score,
    sell_score=agg.sell_score,
    price=price,
    atr=atr,
)
ai = decide(ai_prompt)
logger.info(f"AI decision: action={ai.action} confidence={ai.confidence:.2f} sl={ai.sl} tp={ai.tp} error={ai.error}")

if ai.action == "SKIP" or ai.error:
    log_decision(
        regime, agg.buy_score, agg.sell_score, trigger_fired=True,
        ai_action="SKIP", risk_block_reason=ai.error or "AI_SKIP",
    )
    time.sleep(config.POLL_INTERVAL_SECONDS)
    continue

direction = ai.action
confidence = ai.confidence
sl = ai.sl
tp = ai.tp
```

Also add the three new imports at the top of `main.py`:

```python
from src.journal.reader import get_journal_context
from src.ai_layer.prompt import build_prompt
from src.ai_layer.client import decide
```

- [ ] **Step 4.1: Add imports and remove dead import from `main.py`**

Open `main.py` and:
1. Add after the existing `from src.logger.writer import (...)` block:

```python
from src.journal.reader import get_journal_context
from src.ai_layer.prompt import build_prompt
from src.ai_layer.client import decide
```

2. Remove `get_direction` from the `from src.trigger.gate import ...` line — it is only used in the Phase 1 block being replaced:

```python
# BEFORE
from src.trigger.gate import should_trigger, get_direction
# AFTER
from src.trigger.gate import should_trigger
```

- [ ] **Step 4.2: Replace the Phase 1 placeholder block with the Phase 3 block** (as shown above)

- [ ] **Step 4.3: Write the new test for `tests/test_main.py`**

Append to the existing `tests/test_main.py`:

```python
def test_decide_called_when_trigger_fires():
    """Phase 3: when trigger fires and AI returns SKIP, log_decision is called with trigger_fired=True."""
    import main  # noqa: F401 — verifies importability
    from src.ai_layer.client import AIDecision
    from unittest.mock import patch, MagicMock
    import pandas as pd
    import numpy as np

    price_series = pd.Series([1920.0] * 200)
    mock_candles = pd.DataFrame({
        "open":   price_series,
        "high":   price_series + 1,
        "low":    price_series - 1,
        "close":  price_series,
        "volume": pd.Series([100.0] * 200),
    })
    mock_agg = MagicMock()
    mock_agg.buy_score = 7.0
    mock_agg.sell_score = 1.0

    ai_skip = AIDecision(action="SKIP", error="AI_API_ERROR")

    call_count = {"n": 0}

    def fake_get_last_candle_time():
        call_count["n"] += 1
        if call_count["n"] == 1:
            return "t1"
        raise KeyboardInterrupt  # terminate loop after one candle

    with patch("main.connect", return_value=True), \
         patch("main.is_connected", return_value=True), \
         patch("main.disconnect"), \
         patch("main.get_last_candle_time", side_effect=fake_get_last_candle_time), \
         patch("main.fetch_candles", return_value=mock_candles), \
         patch("main.get_account_info", return_value={"balance": 10000.0, "equity": 10000.0}), \
         patch("main.get_positions", return_value=[]), \
         patch("main.get_kill_switch_state", return_value=False), \
         patch("main.get_daily_start_balance", return_value=(10000.0, "2026-03-25")), \
         patch("main.set_daily_start_balance"), \
         patch("main.sync_positions", return_value=([], [])), \
         patch("main.classify", return_value="TRENDING"), \
         patch("main.run_all", return_value=[]), \
         patch("main.aggregate", return_value=mock_agg), \
         patch("main.should_trigger", return_value=True), \
         patch("main.get_journal_context", return_value=""), \
         patch("main.build_prompt", return_value="test prompt") as mock_prompt, \
         patch("main.decide", return_value=ai_skip) as mock_decide, \
         patch("main.log_decision") as mock_log:
        import main as m
        m.main()

    mock_prompt.assert_called_once()
    mock_decide.assert_called_once_with("test prompt")
    mock_log.assert_called_once()
    call_kwargs = mock_log.call_args.kwargs
    assert call_kwargs.get("trigger_fired") is True
    assert call_kwargs.get("ai_action") == "SKIP"
```

- [ ] **Step 4.4: Run full suite — confirm GREEN**

```
python -m pytest tests/ --ignore=tests/integration -q
```
Expected: 116 passed (115 + 1 new)

- [ ] **Step 4.5: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: wire AI layer into main loop - Phase 3 complete"
```

---

## Task 5: Update `.env.example` and Install Check

- [ ] **Step 5.1: Verify `anthropic` is installed**

```
python -c "import anthropic; print(anthropic.__version__)"
```
Expected: version string printed without error.

If not installed:
```
pip install "anthropic>=0.21.0"
```

- [ ] **Step 5.2: Confirm `ANTHROPIC_API_KEY` is in `.env`**

```
python -c "from src import config; print('key set:', bool(config.ANTHROPIC_API_KEY))"
```
Expected: `key set: True`

If not set, add `ANTHROPIC_API_KEY=sk-ant-...` to `.env`.

- [ ] **Step 5.3: Confirm `.env.example` already has the key**

The existing `.env.example` already contains:
```
# Claude AI (Phase 3)
ANTHROPIC_API_KEY=your_api_key_here
```
If missing, add it. Use `CLAUDE_PRIMARY_MODEL` and `CLAUDE_FALLBACK_MODEL` defaults are in `config.py` so no `.env` entry required unless overriding.

- [ ] **Step 5.4: Final full suite run**

```
python -m pytest tests/ --ignore=tests/integration -v
```
Expected: 116 passed, 0 failed

- [ ] **Step 5.5: Tag**

```bash
git tag v0.2.0-ai
```

---

## Summary

After completion:
- `src/journal/reader.py` — `get_journal_context(n) -> str`
- `src/ai_layer/prompt.py` — `build_prompt(...) -> str`
- `src/ai_layer/client.py` — `decide(prompt) -> AIDecision` (Haiku → Sonnet, no-raise)
- `main.py` — Phase 1 placeholder replaced with real AI pipeline; dead `get_direction` import removed
- 116 unit tests passing
- Tagged `v0.2.0-ai`
