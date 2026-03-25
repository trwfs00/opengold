"""Tests for main.py helper functions — no MT5 or DB required."""
from unittest.mock import MagicMock, patch
import importlib


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
