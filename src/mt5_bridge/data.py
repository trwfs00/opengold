import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone
import logging

from src import config

logger = logging.getLogger(__name__)
SYMBOL = config.SYMBOL
TIMEFRAME = getattr(mt5, f"TIMEFRAME_{config.TIMEFRAME}", mt5.TIMEFRAME_M1)


def fetch_candles(count: int = 200) -> pd.DataFrame:
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, count)
    if rates is None or len(rates) == 0:
        logger.error(f"fetch_candles failed: {mt5.last_error()}")
        return pd.DataFrame()
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.rename(columns={"tick_volume": "volume"})
    return df[["time", "open", "high", "low", "close", "volume"]]


def get_last_candle_time() -> datetime | None:
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 1)
    if rates is None or len(rates) == 0:
        return None
    return pd.to_datetime(rates[0]["time"], unit="s", utc=True).to_pydatetime()


def get_positions() -> list[dict]:
    positions = mt5.positions_get(symbol=SYMBOL)
    if positions is None:
        return []
    return [
        {
            "ticket": p.ticket,
            "symbol": p.symbol,
            "direction": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
            "lots": p.volume,
            "open_price": p.price_open,
            "current_price": p.price_current,
            "unrealized_pnl": p.profit,
            "sl": p.sl,
            "tp": p.tp,
            "open_time": pd.to_datetime(p.time, unit="s", utc=True).isoformat(),
        }
        for p in positions
    ]


def get_history_deals(from_dt: datetime, to_dt: datetime) -> list[dict]:
    deals = mt5.history_deals_get(from_dt, to_dt)
    if deals is None:
        return []
    return [
        {
            "ticket": d.ticket,
            "order": d.order,
            "time": pd.to_datetime(d.time, unit="s", utc=True).to_pydatetime(),
            "type": d.type,
            "volume": d.volume,
            "price": d.price,
            "profit": d.profit,
            "symbol": d.symbol,
            "entry": d.entry,  # 0=IN, 1=OUT
        }
        for d in deals
        if d.symbol == SYMBOL
    ]
