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
    """When trigger fires, decide() is called with the built prompt."""
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
    mock_ai.action = "SKIP"
    mock_ai.error = "AI_API_ERROR"

    with (
        patch("main.fetch_candles", return_value=pd.DataFrame(candle)),
        patch("main.compute_agg", return_value=MagicMock(buy_score=7.0, sell_score=2.0)),
        patch("main.classify_regime", return_value="TRENDING"),
        patch("main.should_trigger", return_value=True),
        patch("main.get_open_trades", return_value=[]),
        patch("main.kill_switch_active", return_value=False),
        patch("main.get_journal_context", return_value=""),
        patch("main.build_prompt", return_value="test prompt"),
        patch("main.decide", return_value=mock_ai) as mock_decide,
        patch("main.log_decision") as mock_log,
        patch("main.time") as mock_time,
    ):
        mock_time.sleep.side_effect = StopIteration
        try:
            run_loop()
        except StopIteration:
            pass

    mock_decide.assert_called_once_with("test prompt")
    assert mock_log.call_args.kwargs.get("trigger_fired") is True
    assert mock_log.call_args.kwargs.get("ai_action") == "SKIP"


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
