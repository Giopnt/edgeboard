"""
Alpha Vantage free API — works from cloud servers, no IP blocking.
Free tier: 25 requests/day (plenty for radar + search).
Get key at: https://www.alphavantage.co/support/#api-key
"""
import logging
import os
import requests
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

AV_BASE = "https://www.alphavantage.co/query"


def _get_key() -> str | None:
    return os.environ.get("ALPHA_VANTAGE_KEY") or os.environ.get("AV_KEY")


def get_daily_prices(symbol: str, months: int = 3) -> pd.DataFrame:
    """
    Fetch daily OHLCV data from Alpha Vantage.
    Returns DataFrame with columns: date, open, high, low, close, volume
    """
    key = _get_key()
    if not key:
        logger.warning("No ALPHA_VANTAGE_KEY set — falling back to yfinance")
        return pd.DataFrame()

    outputsize = "full" if months > 3 else "compact"

    try:
        resp = requests.get(AV_BASE, params={
            "function":   "TIME_SERIES_DAILY",
            "symbol":     symbol,
            "outputsize": outputsize,
            "apikey":     key,
        }, timeout=15)
        data = resp.json()

        if "Time Series (Daily)" not in data:
            logger.warning(f"Alpha Vantage returned no data for {symbol}: {data.get('Note', data.get('Information', 'Unknown error'))}")
            return pd.DataFrame()

        ts = data["Time Series (Daily)"]
        cutoff = datetime.now() - timedelta(days=months * 30)

        rows = []
        for date_str, values in ts.items():
            d = datetime.strptime(date_str, "%Y-%m-%d")
            if d < cutoff:
                continue
            rows.append({
                "date":   d.date(),
                "open":   float(values["1. open"]),
                "high":   float(values["2. high"]),
                "low":    float(values["3. low"]),
                "close":  float(values["4. close"]),
                "volume": int(values["5. volume"]),
            })

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        logger.info(f"Alpha Vantage: {symbol} got {len(df)} rows")
        return df

    except Exception as e:
        logger.error(f"Alpha Vantage failed for {symbol}: {e}")
        return pd.DataFrame()


def search_symbol(query: str) -> list[dict]:
    """Search for stock symbols via Alpha Vantage."""
    key = _get_key()
    if not key:
        return []

    try:
        resp = requests.get(AV_BASE, params={
            "function":  "SYMBOL_SEARCH",
            "keywords":  query,
            "apikey":    key,
        }, timeout=10)
        data = resp.json()
        matches = data.get("bestMatches", [])
        results = []
        for m in matches[:8]:
            results.append({
                "symbol":   m.get("1. symbol", ""),
                "name":     m.get("2. name", ""),
                "exchange": m.get("4. region", ""),
                "type":     m.get("3. type", "Equity"),
                "sector":   None,
            })
        return results
    except Exception as e:
        logger.error(f"Alpha Vantage search failed: {e}")
        return []