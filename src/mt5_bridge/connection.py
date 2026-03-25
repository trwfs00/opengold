import MetaTrader5 as mt5
from src import config
import logging

logger = logging.getLogger(__name__)


def connect() -> bool:
    if not mt5.initialize(
        login=config.MT5_LOGIN,
        password=config.MT5_PASSWORD,
        server=config.MT5_SERVER,
    ):
        logger.error(f"MT5 initialize failed: {mt5.last_error()}")
        return False
    logger.info(f"MT5 connected: {mt5.account_info().name}")
    return True


def disconnect():
    mt5.shutdown()


def is_connected() -> bool:
    return mt5.account_info() is not None


def get_account_info() -> dict:
    info = mt5.account_info()
    if info is None:
        return {}
    return {
        "balance": info.balance,
        "equity": info.equity,
        "currency": info.currency,
    }
