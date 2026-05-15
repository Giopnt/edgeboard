"""
yfinance on cloud servers (Railway, Render, etc.) often gets blocked by Yahoo Finance.
This module patches the yfinance session with proper headers to fix it.
Import this at the top of any file that uses yfinance.
"""
import requests
import yfinance as yf


def get_session() -> requests.Session:
    """Create a requests session that mimics a real browser."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    })
    return session


def get_ticker(symbol: str) -> yf.Ticker:
    """Get a yfinance Ticker with a proper browser session."""
    return yf.Ticker(symbol, session=get_session())


def get_history(symbol: str, period: str = "6mo") -> "pd.DataFrame":
    """Fetch price history with browser session to avoid cloud IP blocking."""
    ticker = get_ticker(symbol)
    hist = ticker.history(period=period)
    if hist.empty and period == "6mo":
        hist = ticker.history(period="3mo")
    return hist