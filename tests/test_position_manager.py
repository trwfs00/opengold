"""Tests for src/executor/position_manager.py — trailing stop + AI re-evaluation."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

from src.executor import position_manager
from src.executor.position_manager import (
    _trail_sl, _should_reeval, _build_reeval_prompt,
    manage_positions, _be_reached, _last_reeval, _partial_closed,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_candles(n: int = 20, base: float = 4400.0, spread: float = 10.0):
    """Create a simple candle DataFrame for ATR computation."""
    times = pd.date_range("2026-03-26", periods=n, freq="1min", tz="UTC")
    rng = np.random.default_rng(42)
    close = base + rng.standard_normal(n).cumsum()
    high = close + spread * rng.random(n)
    low = close - spread * rng.random(n)
    return pd.DataFrame({
        "time": times, "open": close, "high": high, "low": low,
        "close": close, "volume": [100] * n,
    })


def _make_pos(ticket=1001, direction="BUY", entry=4400.0, current=4420.0,
              sl=4380.0, tp=4440.0, pnl=20.0):
    return {
        "ticket": ticket,
        "symbol": "XAUUSD",
        "direction": direction,
        "lots": 0.09,
        "open_price": entry,
        "current_price": current,
        "unrealized_pnl": pnl,
        "sl": sl,
        "tp": tp,
        "open_time": "2026-03-26T18:25:00+00:00",
    }


@pytest.fixture(autouse=True)
def _clean_state():
    """Clear module-level state between tests."""
    _be_reached.clear()
    _last_reeval.clear()
    _partial_closed.clear()
    yield
    _be_reached.clear()
    _last_reeval.clear()
    _partial_closed.clear()


# ── Trailing SL tests ───────────────────────────────────────────────────────

class TestTrailSL:
    def test_no_move_before_be_ratio(self):
        """Don't move SL when profit is below BE ratio."""
        # TP at 4440, entry 4400 → TP dist = 40. BE target = 4400 + 40*0.5 = 4420
        # Current 4410 → below BE target
        pos = _make_pos(current=4410.0)
        assert _trail_sl(pos, atr=5.0) is None

    def test_breakeven_triggered(self):
        """Move SL to entry when price reaches BE ratio."""
        # TP dist = 40, BE target = 4420, current = 4425 → triggers BE
        pos = _make_pos(current=4425.0, sl=4380.0)
        result = _trail_sl(pos, atr=5.0)
        assert result is not None
        new_sl, event_type = result
        assert new_sl == 4400.0  # entry price = breakeven
        assert event_type == "TRAIL_BE"
        assert pos["ticket"] in _be_reached

    def test_atr_trail_after_be(self):
        """After breakeven, SL trails at current − ATR × mult."""
        _be_reached.add(1001)
        # current=4430, atr=5, mult=1.5 → trail SL = 4430 − 7.5 = 4422.5
        pos = _make_pos(current=4430.0, sl=4400.0)
        result = _trail_sl(pos, atr=5.0)
        assert result is not None
        new_sl, event_type = result
        assert new_sl == 4422.5
        assert event_type == "TRAIL_SL"

    def test_trail_never_moves_backwards(self):
        """SL never moves down (for BUY)."""
        _be_reached.add(1001)
        # current − atr*mult = 4410 − 7.5 = 4402.5, but current SL=4410 → no move
        pos = _make_pos(current=4410.0, sl=4410.0)
        new_sl = _trail_sl(pos, atr=5.0)
        assert new_sl is None

    def test_sell_breakeven(self):
        """SELL position: breakeven when price drops enough."""
        # Entry 4400, TP 4360 → TP dist = 40, BE target = 4400 − 20 = 4380
        # Current 4375 → below BE target → triggers
        pos = _make_pos(direction="SELL", entry=4400.0, current=4375.0,
                        sl=4420.0, tp=4360.0)
        result = _trail_sl(pos, atr=5.0)
        assert result is not None
        new_sl, event_type = result
        assert new_sl == 4400.0  # breakeven
        assert event_type == "TRAIL_BE"

    def test_sell_atr_trail(self):
        """SELL: trail SL at current + ATR × mult."""
        _be_reached.add(1001)
        # current=4370, atr=5, mult=1.5 → trail = 4370 + 7.5 = 4377.5
        pos = _make_pos(direction="SELL", entry=4400.0, current=4370.0,
                        sl=4400.0, tp=4360.0)
        result = _trail_sl(pos, atr=5.0)
        assert result is not None
        new_sl, event_type = result
        assert new_sl == 4377.5
        assert event_type == "TRAIL_SL"

    def test_sell_trail_never_increases(self):
        """SELL: SL never moves up (higher) once trailing."""
        _be_reached.add(1001)
        # trail would be 4370+7.5=4377.5, but SL already at 4375 (lower = better)
        pos = _make_pos(direction="SELL", entry=4400.0, current=4370.0,
                        sl=4375.0, tp=4360.0)
        new_sl = _trail_sl(pos, atr=5.0)
        assert new_sl is None

    def test_no_tp_skips(self):
        """Position with TP=0 should be skipped when TRAIL_MIN_PROFIT_USD is 0."""
        pos = _make_pos(tp=0.0)
        assert _trail_sl(pos, atr=5.0) is None

    def test_no_tp_triggers_via_usd_profit(self):
        """Position with TP=0 should still trail when USD profit >= TRAIL_MIN_PROFIT_USD."""
        # BUY at 4400, currently at 4420 (+20 pips), pnl=$100
        pos = _make_pos(tp=0.0, current=4420.0, sl=4380.0, pnl=100.0)
        with patch.object(position_manager.config, "TRAIL_MIN_PROFIT_USD", 100.0):
            result = _trail_sl(pos, atr=5.0)
        # BE should trigger → move SL to entry
        assert result == (4400.0, "TRAIL_BE")

    def test_no_tp_no_trail_below_usd_threshold(self):
        """Position with TP=0 should NOT trail when USD profit < TRAIL_MIN_PROFIT_USD."""
        pos = _make_pos(tp=0.0, current=4420.0, sl=4380.0, pnl=50.0)
        with patch.object(position_manager.config, "TRAIL_MIN_PROFIT_USD", 100.0):
            result = _trail_sl(pos, atr=5.0)
        assert result is None

    def test_nan_atr_skips_phase2(self):
        """NaN ATR in Phase 2 should not move SL (was silently computing NaN before)."""
        import math
        pos = _make_pos(current=4420.0, sl=4400.0)  # SL already at entry
        _be_reached.add(1001)  # already in Phase 2
        result = _trail_sl(pos, atr=float("nan"))
        assert result is None


# ── AI Re-evaluation tests ──────────────────────────────────────────────────

class TestReeval:
    def test_counter_signal_needed(self):
        """Don't re-eval when counter-signal is weak."""
        pos = _make_pos(direction="BUY")
        # BUY position, sell_score=3.0 (below threshold 5.0)
        assert _should_reeval(pos, buy_score=8.0, sell_score=3.0) is False

    def test_strong_counter_triggers(self):
        """Strong counter-signal triggers re-evaluation."""
        pos = _make_pos(direction="BUY")
        assert _should_reeval(pos, buy_score=2.0, sell_score=6.0) is True

    def test_cooldown_respected(self):
        """Don't re-eval if cooldown hasn't elapsed."""
        pos = _make_pos()
        _last_reeval[1001] = datetime.now(timezone.utc)
        assert _should_reeval(pos, buy_score=2.0, sell_score=6.0) is False

    def test_cooldown_expired(self):
        """Re-eval allowed after cooldown expires."""
        pos = _make_pos()
        _last_reeval[1001] = datetime.now(timezone.utc) - timedelta(minutes=10)
        assert _should_reeval(pos, buy_score=2.0, sell_score=6.0) is True

    def test_disabled_when_interval_zero(self):
        """REEVAL_INTERVAL_MINUTES=0 disables re-evaluation."""
        pos = _make_pos()
        with patch.object(position_manager.config, "REEVAL_INTERVAL_MINUTES", 0):
            assert _should_reeval(pos, buy_score=1.0, sell_score=8.0) is False

    def test_sell_counter_is_buy_score(self):
        """For SELL, counter-signal is buy_score."""
        pos = _make_pos(direction="SELL")
        assert _should_reeval(pos, buy_score=6.0, sell_score=1.0) is True


class TestReevalPrompt:
    def test_prompt_contains_position_info(self):
        pos = _make_pos(pnl=50.0)
        prompt = _build_reeval_prompt(pos, "TRENDING_UP", 2.0, 7.0, 5.5)
        assert "BUY" in prompt
        assert "4400" in prompt
        assert "+50.00" in prompt
        assert "HOLD" in prompt
        assert "CLOSE" in prompt


# ── Integration test: manage_positions ───────────────────────────────────────

class TestManagePositions:
    @patch("src.executor.position_manager.log_position_event")
    @patch("src.executor.position_manager.modify_sl")
    def test_trail_calls_modify_sl(self, mock_modify, _mock_log):
        """When trailing triggers, modify_sl is called."""
        mock_modify.return_value = True
        candles = _make_candles()
        # Price far above BE target → should trigger BE
        pos = _make_pos(current=4435.0, sl=4380.0)
        with patch.object(position_manager.config, "DRY_RUN", False):
            manage_positions([pos], candles, "TRENDING_UP", 8.0, 2.0)
        mock_modify.assert_called_once()
        call_args = mock_modify.call_args
        assert call_args[0][0] == 1001  # ticket
        assert call_args[0][1] == 4400.0  # breakeven entry

    @patch("src.executor.position_manager.log_position_event")
    @patch("src.executor.position_manager.close_position")
    @patch("src.executor.position_manager.decide")
    @patch("src.executor.position_manager.modify_sl")
    def test_reeval_close(self, mock_modify, mock_decide, mock_close, _mock_log):
        """When AI says CLOSE, close_position is called."""
        mock_modify.return_value = True
        mock_close.return_value = True
        mock_decide.return_value = MagicMock(action="CLOSE", reasoning="reversal")
        candles = _make_candles()
        pos = _make_pos(current=4410.0)  # below BE, trail won't fire
        with patch.object(position_manager.config, "REEVAL_MIN_COUNTER_SCORE", 3.0):
            manage_positions([pos], candles, "TRENDING_DOWN", 2.0, 7.0)
        mock_decide.assert_called_once()
        mock_close.assert_called_once_with(1001, dry_run=False)

    @patch("src.executor.position_manager.log_position_event")
    @patch("src.executor.position_manager.close_position")
    @patch("src.executor.position_manager.decide")
    @patch("src.executor.position_manager.modify_sl")
    def test_reeval_hold(self, mock_modify, mock_decide, mock_close, _mock_log):
        """When AI says HOLD, position stays open."""
        mock_decide.return_value = MagicMock(action="HOLD", reasoning="support holds")
        candles = _make_candles()
        pos = _make_pos(current=4410.0)
        with patch.object(position_manager.config, "REEVAL_MIN_COUNTER_SCORE", 3.0):
            manage_positions([pos], candles, "TRENDING_DOWN", 2.0, 7.0)
        mock_decide.assert_called_once()
        mock_close.assert_not_called()

    @patch("src.executor.position_manager.log_position_event")
    @patch("src.executor.position_manager.modify_sl")
    def test_cleanup_stale_state(self, mock_modify, _mock_log):
        """Positions that no longer exist are cleaned from state."""
        _be_reached.add(9999)  # stale ticket
        _last_reeval[9999] = datetime.now(timezone.utc)
        candles = _make_candles()
        pos = _make_pos(current=4410.0)
        manage_positions([pos], candles, "RANGING", 3.0, 3.0)
        assert 9999 not in _be_reached
        assert 9999 not in _last_reeval


# ── log_position_event ────────────────────────────────────────────────────────

class TestLogPositionEvent:
    @patch("src.logger.writer.execute")
    def test_trail_be_logged(self, mock_exec):
        """log_position_event writes TRAIL_BE row to DB."""
        from src.logger.writer import log_position_event
        log_position_event(1001, "TRAIL_BE", "BUY", 4420.0, old_sl=4380.0, new_sl=4400.0)
        mock_exec.assert_called_once()
        sql, params = mock_exec.call_args[0]
        assert "position_events" in sql
        assert params[1] == "TRAIL_BE"
        assert params[3] == 4380.0   # old_sl
        assert params[4] == 4400.0   # new_sl

    @patch("src.logger.writer.execute")
    def test_reeval_close_logged_with_reasoning(self, mock_exec):
        """REEVAL_CLOSE includes reasoning in DB row."""
        from src.logger.writer import log_position_event
        log_position_event(1002, "REEVAL_CLOSE", "SELL", 4380.0, reasoning="trend reversed")
        mock_exec.assert_called_once()
        _, params = mock_exec.call_args[0]
        assert params[1] == "REEVAL_CLOSE"
        assert params[6] == "trend reversed"

    @patch("src.logger.writer.execute", side_effect=Exception("db error"))
    def test_db_error_does_not_raise(self, _mock_exec):
        """log_position_event swallows DB errors gracefully."""
        from src.logger.writer import log_position_event
        log_position_event(1003, "TRAIL_SL", "BUY", 4430.0)  # should not raise

    @patch("src.executor.position_manager.log_position_event")
    @patch("src.executor.position_manager.modify_sl")
    def test_manage_positions_logs_trail_be(self, mock_modify, mock_log):
        """manage_positions calls log_position_event for TRAIL_BE."""
        candles = _make_candles()
        pos = _make_pos(current=4435.0, sl=4380.0)
        with patch.object(position_manager.config, "DRY_RUN", False):
            manage_positions([pos], candles, "TRENDING_UP", 8.0, 2.0)
        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args[1]
        assert call_kwargs["event_type"] == "TRAIL_BE"
        assert call_kwargs["ticket"] == 1001

    @patch("src.executor.position_manager.log_position_event")
    @patch("src.executor.position_manager.close_position")
    @patch("src.executor.position_manager.decide")
    @patch("src.executor.position_manager.modify_sl")
    def test_manage_positions_logs_reeval_close(self, _mock_modify, mock_decide, _mock_close, mock_log):
        """manage_positions calls log_position_event with REEVAL_CLOSE."""
        mock_decide.return_value = MagicMock(action="CLOSE", reasoning="reversal detected")
        candles = _make_candles()
        pos = _make_pos(current=4410.0)
        with patch.object(position_manager.config, "REEVAL_MIN_COUNTER_SCORE", 3.0):
            manage_positions([pos], candles, "TRENDING_DOWN", 2.0, 7.0)
        # Find the REEVAL_CLOSE log call
        reeval_calls = [c for c in mock_log.call_args_list
                        if c[1].get("event_type") == "REEVAL_CLOSE"]
        assert len(reeval_calls) == 1
        assert reeval_calls[0][1]["reasoning"] == "reversal detected"


# ── Partial Close tests ───────────────────────────────────────────────────────

class TestPartialClose:
    @patch("src.executor.position_manager.log_position_event")
    @patch("src.executor.position_manager.partial_close_position")
    @patch("src.executor.position_manager.decide")
    @patch("src.executor.position_manager.modify_sl")
    def test_partial_close_called(self, _mock_modify, mock_decide, mock_partial, _mock_log):
        """When AI says PARTIAL_CLOSE, partial_close_position is called with correct lots."""
        mock_decide.return_value = MagicMock(action="PARTIAL_CLOSE", reasoning="mixed signal")
        mock_partial.return_value = True
        candles = _make_candles()
        pos = _make_pos(current=4410.0)        # pos has lots=0.09
        with patch.object(position_manager.config, "REEVAL_MIN_COUNTER_SCORE", 3.0), \
             patch.object(position_manager.config, "PARTIAL_CLOSE_RATIO", 0.5):
            manage_positions([pos], candles, "TRENDING_DOWN", 2.0, 7.0)
        mock_partial.assert_called_once()
        call_args = mock_partial.call_args[0]
        assert call_args[0] == 1001          # ticket
        assert call_args[1] == 0.04          # 0.09 * 0.5 = 0.045 → rounded to 0.04

    @patch("src.executor.position_manager.log_position_event")
    @patch("src.executor.position_manager.partial_close_position")
    @patch("src.executor.position_manager.decide")
    @patch("src.executor.position_manager.modify_sl")
    def test_partial_close_only_once(self, _mock_modify, mock_decide, mock_partial, _mock_log):
        """A position can only be partially closed once."""
        mock_decide.return_value = MagicMock(action="PARTIAL_CLOSE", reasoning="hedge")
        mock_partial.return_value = True
        candles = _make_candles()
        pos = _make_pos(current=4410.0)
        with patch.object(position_manager.config, "REEVAL_MIN_COUNTER_SCORE", 3.0):
            # First call — should partial close
            manage_positions([pos], candles, "TRENDING_DOWN", 2.0, 7.0)
            assert 1001 in _partial_closed
            mock_partial.reset_mock()
            # Reset cooldown to force re-eval
            _last_reeval.clear()
            # Second call with same ticket — should NOT partial close again
            manage_positions([pos], candles, "TRENDING_DOWN", 2.0, 7.0)
        mock_partial.assert_not_called()

    @patch("src.executor.position_manager.partial_close_position")
    @patch("src.executor.position_manager.decide")
    @patch("src.executor.position_manager.modify_sl")
    def test_partial_close_logs_event(self, _mock_modify, mock_decide, mock_partial):
        """Partial close logs PARTIAL_CLOSE event_type."""
        mock_decide.return_value = MagicMock(action="PARTIAL_CLOSE", reasoning="take some profit")
        mock_partial.return_value = True
        candles = _make_candles()
        pos = _make_pos(current=4410.0)
        with patch.object(position_manager.config, "REEVAL_MIN_COUNTER_SCORE", 3.0), \
             patch("src.executor.position_manager.log_position_event") as mock_log:
            manage_positions([pos], candles, "TRENDING_DOWN", 2.0, 7.0)
        partial_calls = [c for c in mock_log.call_args_list
                         if c[1].get("event_type") == "PARTIAL_CLOSE"]
        assert len(partial_calls) == 1
        assert partial_calls[0][1]["reasoning"] == "take some profit"

    @patch("src.executor.position_manager.log_position_event")
    @patch("src.executor.position_manager.partial_close_position")
    @patch("src.executor.position_manager.decide")
    @patch("src.executor.position_manager.modify_sl")
    def test_partial_close_state_cleared_when_position_closes(self, _mock_modify, mock_decide, mock_partial, _mock_log):
        """When position closes (disappears), _partial_closed state is cleaned."""
        _partial_closed.add(9999)
        candles = _make_candles()
        pos = _make_pos(current=4410.0)  # ticket=1001, not 9999
        manage_positions([pos], candles, "RANGING", 3.0, 3.0)
        assert 9999 not in _partial_closed

    def test_prompt_mentions_partial_close(self):
        """Reeval prompt contains PARTIAL_CLOSE option when not already partial closed."""
        pos = _make_pos()
        prompt = _build_reeval_prompt(pos, "RANGING", 3.0, 6.0, 5.0)
        assert "PARTIAL_CLOSE" in prompt

    def test_prompt_hides_partial_close_after_first(self):
        """Prompt does NOT offer PARTIAL_CLOSE when position already partially closed."""
        _partial_closed.add(1001)
        pos = _make_pos()
        prompt = _build_reeval_prompt(pos, "RANGING", 3.0, 6.0, 5.0)
        # Should only offer HOLD or CLOSE
        assert '"HOLD"|"CLOSE"' in prompt
        assert "PARTIAL_CLOSE" not in prompt.split("[TASK]")[1]


# ── partial_close_position (orders.py) ───────────────────────────────────────

class TestPartialCloseOrder:
    def test_dry_run_returns_true(self):
        """Dry run short-circuits without MT5 call."""
        from src.executor.orders import partial_close_position
        assert partial_close_position(1001, 0.05, dry_run=True) is True

    def test_position_not_found(self):
        """Returns False if MT5 has no matching position."""
        from src.executor.orders import partial_close_position
        import MetaTrader5 as mt5
        with patch("src.executor.orders.mt5") as mock_mt5:
            mock_mt5.positions_get.return_value = []
            assert partial_close_position(1001, 0.05, dry_run=False) is False

    def test_lots_below_min_blocked(self):
        """Returns False if close_lots is below MT5 minimum volume."""
        from src.executor.orders import partial_close_position
        mock_pos = MagicMock()
        mock_pos.volume = 0.10
        mock_pos.type = 0   # ORDER_TYPE_BUY
        mock_info = MagicMock()
        mock_info.volume_min = 0.01
        with patch("src.executor.orders.mt5") as mock_mt5:
            mock_mt5.positions_get.return_value = [mock_pos]
            mock_mt5.symbol_info.return_value = mock_info
            # close_lots=0.001 rounds to 0.00 < 0.01 min
            result = partial_close_position(1001, 0.001, dry_run=False)
        assert result is False
