"""
yfinance on cloud servers gets blocked by Yahoo Finance.
This module provides multiple fallback strategies.
"""
import time
import logging
import requests
import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]

_ua_index = 0


def get_session() -> requests.Session:
    """Create a session that rotates user agents."""
    global _ua_index
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENTS[_ua_index % len(USER_AGENTS)],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })
    _ua_index += 1
    return session


def get_ticker(symbol: str) -> yf.Ticker:
    return yf.Ticker(symbol, session=get_session())


def get_history(symbol: str, period: str = "6mo") -> pd.DataFrame:
    """
    Fetch price history with multiple fallback strategies.
    Tries yfinance first, falls back to shorter periods if blocked.
    """
    periods_to_try = [period, "3mo", "1mo"] if period == "6mo" else [period, "1mo"]

    for p in periods_to_try:
        try:
            session = get_session()
            ticker = yf.Ticker(symbol, session=session)
            hist = ticker.history(period=p)
            if not hist.empty and len(hist) >= 10:
                logger.info(f"{symbol}: got {len(hist)} rows for period={p}")
                return hist
            time.sleep(0.3)  # Small delay between retries
        except Exception as e:
            logger.warning(f"{symbol} period={p} failed: {e}")
            time.sleep(0.5)

    # Last resort — try download function
    try:
        hist = yf.download(
            symbol,
            period="3mo",
            auto_adjust=True,
            progress=False,
        )
        if not hist.empty:
            return hist
    except Exception as e:
        logger.error(f"{symbol} download fallback failed: {e}")

    return pd.DataFrame()