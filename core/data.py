"""
core/data.py
Fetch historical OHLC and live quotes from Kite.
"""

import pandas as pd
from datetime import datetime, timedelta
from kiteconnect import KiteConnect


INTERVAL_MAP = {
    "1 min": "minute",
    "3 min": "3minute",
    "5 min": "5minute",
    "15 min": "15minute",
    "30 min": "30minute",
    "1 hour": "60minute",
    "1 day": "day",
}


def fetch_historical(
    kite: KiteConnect,
    instrument_token: int,
    from_date: datetime,
    to_date: datetime,
    interval: str = "day",
) -> pd.DataFrame:
    """Fetch OHLCV data from Kite and return as DataFrame."""
    data = kite.historical_data(
        instrument_token,
        from_date=from_date,
        to_date=to_date,
        interval=interval,
    )
    df = pd.DataFrame(data)
    df.rename(columns={"date": "datetime"}, inplace=True)
    return df


def search_instruments(kite: KiteConnect, query: str, exchange: str = "NSE") -> list[dict]:
    """Search instruments by name/symbol."""
    try:
        instruments = kite.instruments(exchange)
        query_upper = query.upper()
        matches = [
            i for i in instruments
            if query_upper in i["tradingsymbol"].upper()
            or query_upper in i.get("name", "").upper()
        ]
        return matches[:20]
    except Exception as e:
        return []


def get_ltp(kite: KiteConnect, instruments: list[str]) -> dict:
    """Get last traded price for a list of instruments like ['NSE:INFY']."""
    try:
        return kite.ltp(instruments)
    except Exception as e:
        return {}


def get_quote(kite: KiteConnect, instrument: str) -> dict:
    """Full quote for a single instrument."""
    try:
        return kite.quote([instrument])
    except Exception as e:
        return {}
