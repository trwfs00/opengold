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
