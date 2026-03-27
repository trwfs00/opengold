# tests/test_executor_orders.py
from unittest.mock import MagicMock, patch, call


def _make_mt5_module():
    """Return a MagicMock that stands in for the MetaTrader5 module."""
    mt5 = MagicMock()
    mt5.ORDER_TYPE_BUY = 0
    mt5.ORDER_TYPE_SELL = 1
    mt5.TRADE_ACTION_DEAL = 1
    mt5.ORDER_TIME_GTC = 0
    mt5.ORDER_FILLING_IOC = 1
    mt5.TRADE_RETCODE_DONE = 10009
    return mt5


def test_place_order_dry_run():
    """dry_run=True returns success dict without calling order_send."""
    with patch("src.executor.orders.mt5", _make_mt5_module()) as mock_mt5:
        from src.executor.orders import place_order
        result = place_order("BUY", 0.01, 1918.0, 1945.0, dry_run=True)
    assert result == {"success": True, "ticket": 0, "price": 0.0, "dry_run": True}
    mock_mt5.order_send.assert_not_called()


def test_place_order_buy_success():
    """Successful BUY order returns ticket and price."""
    mock_mt5 = _make_mt5_module()
    tick = MagicMock()
    tick.ask = 1923.0
    mock_mt5.symbol_info_tick.return_value = tick
    order_result = MagicMock()
    order_result.retcode = mock_mt5.TRADE_RETCODE_DONE
    order_result.order = 12345
    order_result.price = 1923.0
    mock_mt5.order_send.return_value = order_result

    with patch("src.executor.orders.mt5", mock_mt5):
        from src.executor.orders import place_order
        result = place_order("BUY", 0.01, 1918.0, 1945.0)
    assert result["success"] is True
    assert result["ticket"] == 12345


def test_place_order_sell_success():
    """Successful SELL order uses bid price."""
    mock_mt5 = _make_mt5_module()
    tick = MagicMock()
    tick.bid = 1922.0
    mock_mt5.symbol_info_tick.return_value = tick
    order_result = MagicMock()
    order_result.retcode = mock_mt5.TRADE_RETCODE_DONE
    order_result.order = 99999
    order_result.price = 1922.0
    mock_mt5.order_send.return_value = order_result

    with patch("src.executor.orders.mt5", mock_mt5):
        from src.executor.orders import place_order
        result = place_order("SELL", 0.01, 1940.0, 1910.0)
    assert result["success"] is True


def test_place_order_uses_config_symbol(monkeypatch):
    """place_order must use config.SYMBOL, not a hardcoded constant."""
    from src import config
    monkeypatch.setattr(config, "SYMBOL", "GBPUSD")

    mock_mt5 = _make_mt5_module()
    tick = MagicMock()
    tick.ask = 1.08500
    mock_mt5.symbol_info_tick.return_value = tick

    order_result = MagicMock()
    order_result.retcode = mock_mt5.TRADE_RETCODE_DONE
    order_result.order = 12345
    order_result.price = 1.08500
    mock_mt5.order_send.return_value = order_result

    with patch("src.executor.orders.mt5", mock_mt5):
        from src.executor.orders import place_order
        result = place_order("BUY", 0.10, 1.0810, 1.0900, dry_run=False)

    assert result["success"] is True
    call_args = mock_mt5.order_send.call_args[0][0]
    assert call_args["symbol"] == "GBPUSD"


def test_place_order_rejected():
    """Rejected order returns success=False with retcode and comment."""
    mock_mt5 = _make_mt5_module()
    tick = MagicMock()
    tick.ask = 1923.0
    mock_mt5.symbol_info_tick.return_value = tick
    order_result = MagicMock()
    order_result.retcode = 10006
    order_result.comment = "rejected"
    mock_mt5.order_send.return_value = order_result

    with patch("src.executor.orders.mt5", mock_mt5):
        from src.executor.orders import place_order
        result = place_order("BUY", 0.01, 1918.0, 1945.0)
    assert result["success"] is False
    assert result["retcode"] == 10006
    assert result["comment"] == "rejected"


def test_place_order_no_tick():
    """No tick data returns success=False with descriptive comment."""
    mock_mt5 = _make_mt5_module()
    mock_mt5.symbol_info_tick.return_value = None

    with patch("src.executor.orders.mt5", mock_mt5):
        from src.executor.orders import place_order
        result = place_order("BUY", 0.01, 1918.0, 1945.0)
    assert result["success"] is False
    assert result["comment"] == "no tick data"
