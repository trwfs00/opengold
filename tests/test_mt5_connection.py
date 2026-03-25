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
