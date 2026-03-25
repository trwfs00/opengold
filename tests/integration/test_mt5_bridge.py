import os
import pytest

# Integration tests — require MT5 running and connected on Windows
# Run with: pytest tests/integration/ -v -m integration


@pytest.mark.integration
def test_mt5_connect_and_fetch():
    from src.mt5_bridge.connection import connect, disconnect, get_account_info
    from src.mt5_bridge.data import fetch_candles, get_last_candle_time, get_positions

    assert connect(), "MT5 connection failed — is MetaTrader5 running?"
    info = get_account_info()
    assert info["balance"] > 0, "Balance should be positive on demo account"

    candles = fetch_candles(50)
    assert len(candles) == 50
    assert "close" in candles.columns
    assert "high" in candles.columns

    last_time = get_last_candle_time()
    assert last_time is not None

    positions = get_positions()
    assert isinstance(positions, list)

    disconnect()
