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
