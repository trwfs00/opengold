from unittest.mock import patch
from importlib import reload
import src.logger.writer as _w


def test_log_decision_persists_signals():
    """log_decision passes signals JSON string to execute()."""
    import json
    reload(_w)
    signals = {"ma_crossover": {"signal": "BUY", "confidence": 0.85}}
    with patch("src.logger.writer.execute") as mock_exec:
        _w.log_decision("TRENDING", 7.5, 1.2, True, signals=signals)
        call_args = mock_exec.call_args[0]
        params = call_args[1]
        assert params[-2] == json.dumps(signals)


def test_log_decision_signals_none_by_default():
    """log_decision passes None for signals when not provided."""
    reload(_w)
    with patch("src.logger.writer.execute") as mock_exec:
        _w.log_decision("RANGING", 3.0, 4.0, False)
        call_args = mock_exec.call_args[0]
        params = call_args[1]
        assert params[-2] is None  # signals slot
