"""Tests for main.py helper functions — no MT5 or DB required."""
from unittest.mock import MagicMock, patch
import importlib
import pandas as pd
from datetime import datetime


def test_main_importable():
    """main.py must be importable without error."""
    import main  # noqa: F401


def test_connect_with_retry_succeeds_first_try():
    """connect_with_retry returns True immediately when connect() returns True."""
    from main import connect_with_retry

    with patch("main.connect", return_value=True):
        assert connect_with_retry(retries=3) is True


def test_connect_with_retry_fails_all():
    """connect_with_retry returns False after all retries are exhausted."""
    from main import connect_with_retry

    with patch("main.connect", return_value=False), \
         patch("main.time.sleep"):   # don't actually wait
        assert connect_with_retry(retries=2) is False


def test_connect_with_retry_succeeds_on_second():
    """connect_with_retry returns True when first attempt fails, second succeeds."""
    from main import connect_with_retry

    side_effects = [False, True]
    with patch("main.connect", side_effect=side_effects), \
         patch("main.time.sleep"):
        assert connect_with_retry(retries=3) is True


def test_decide_called_when_trigger_fires():
    """When trigger fires (hot_signal=True), decide() is called with the built prompt."""
    from main import run_loop
    candle = {
        "time": [datetime(2026, 3, 25, 10, i) for i in range(20)],
        "open":  [1920.0] * 20,
        "high":  [1925.0] * 20,
        "low":   [1915.0] * 20,
        "close": [1922.0] * 20,
        "vol":   [1000.0] * 20,
    }
    mock_ai = MagicMock()
    mock_ai.action = "BUY"
    mock_ai.confidence = 0.8
    mock_ai.sl = 1905.0
    mock_ai.tp = 1945.0
    mock_ai.error = None
    mock_ai.reasoning = None
    mock_risk = MagicMock(approved=False, block_reason="TEST_BLOCK")

    with (
        patch("main.fetch_candles", return_value=pd.DataFrame(candle)),
        patch("main.run_all", return_value={}),
        patch("main.compute_agg", return_value=MagicMock(buy_score=7.0, sell_score=2.0, signals={})),
        patch("main.classify_regime", return_value="TRENDING"),
        patch("main.sync_positions", return_value=([], [])),
        patch("main.get_kill_switch_state", return_value=False),
        patch("main.config") as mock_cfg,
        patch("main.get_journal_context", return_value=""),
        patch("main.build_prompt", return_value="test prompt"),
        patch("main.decide", return_value=mock_ai) as mock_decide,
        patch("main.validate", return_value=mock_risk),
        patch("main.get_account_info", return_value={"balance": 10000.0, "equity": 10000.0}),
        patch("main._check_daily_reset"),
        patch("main.get_daily_start_balance", return_value=(10000.0, "2026-03-25")),
        patch("main.execute", return_value=[(0,)]),
        patch("main.log_decision") as mock_log,
        patch("main.time") as mock_time,
    ):
        # Configure config mock to enable hot_signal path
        mock_cfg.POLL_INTERVAL_SECONDS = 1
        mock_cfg.MT5_RECONNECT_RETRIES = 1
        mock_cfg.MAX_CONCURRENT_TRADES = 10
        mock_cfg.TRIGGER_MIN_SCORE = 6.0
        mock_cfg.TRIGGER_MIN_SCORE_DIFF = 4.0
        mock_cfg.AI_INTERVAL_MINUTES = 5
        mock_cfg.DRY_RUN = True
        mock_cfg.DAILY_DRAWDOWN_LIMIT = 0.05
        mock_time.sleep.side_effect = StopIteration
        try:
            run_loop()
        except StopIteration:
            pass

    mock_decide.assert_called_once_with("test prompt")
    assert mock_log.call_args.kwargs.get("trigger_fired") is True
    assert mock_log.call_args.kwargs.get("ai_action") == "BUY"


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


def test_drawdown_activates_kill_switch():
    """When equity drops below daily drawdown limit, kill switch is auto-engaged."""
    from main import run_loop
    candle = {
        "time": [datetime(2026, 3, 25, 10, i) for i in range(20)],
        "open":  [1920.0] * 20,
        "high":  [1925.0] * 20,
        "low":   [1915.0] * 20,
        "close": [1922.0] * 20,
        "vol":   [1000.0] * 20,
    }
    with (
        patch("main.fetch_candles", return_value=pd.DataFrame(candle)),
        patch("main.run_all", return_value={}),
        patch("main.compute_agg", return_value=MagicMock(buy_score=1.0, sell_score=1.0, signals={})),
        patch("main.classify_regime", return_value="RANGING"),
        patch("main.sync_positions", return_value=([], [])),
        patch("main.get_kill_switch_state", return_value=False),
        patch("main.config") as mock_cfg,
        # Equity 9500 vs daily_start 10000 → -5% → exceeds 3% limit
        patch("main.get_account_info", return_value={"balance": 9800.0, "equity": 9500.0}),
        patch("main._check_daily_reset"),
        patch("main.get_daily_start_balance", return_value=(10000.0, "2026-03-25")),
        patch("main.set_kill_switch") as mock_set_kill,
        patch("main.log_decision"),
        patch("main.time") as mock_time,
    ):
        mock_cfg.DAILY_DRAWDOWN_LIMIT = 0.03
        mock_cfg.POLL_INTERVAL_SECONDS = 1
        mock_cfg.MAX_CONCURRENT_TRADES = 10
        mock_cfg.TRIGGER_MIN_SCORE = 6.0
        mock_cfg.TRIGGER_MIN_SCORE_DIFF = 4.0
        mock_cfg.AI_INTERVAL_MINUTES = 5
        mock_time.sleep.side_effect = StopIteration
        try:
            run_loop()
        except StopIteration:
            pass

    mock_set_kill.assert_called_once_with(True)
