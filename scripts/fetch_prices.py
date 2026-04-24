#!/usr/bin/env python3
"""
Fetch and store latest price data for all watchlist tickers.

Run manually:
    cd edgeboard/backend
    source .venv/bin/activate
    PYTHONPATH=. python ../scripts/fetch_prices.py

Runs automatically via launchd every weekday morning (see scripts/install_jobs.sh)
"""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import yfinance as yf
from app.db.database import SessionLocal
from app.models.ticker import Ticker
from app.models.price import PriceHistory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def fetch_for_ticker(db, ticker):
    yf_ticker = yf.Ticker(ticker.symbol)
    hist = yf_ticker.history(period="7d")  # Only fetch recent days

    if hist.empty:
        logger.warning(f"{ticker.symbol}: No data returned from yfinance")
        return 0

    existing_dates = {
        row.date for row in db.query(PriceHistory.date)
        .filter(PriceHistory.ticker_id == ticker.id).all()
    }

    added = 0
    prev_close = None

    for ts, row in hist.iterrows():
        record_date = ts.date()
        if record_date in existing_dates:
            prev_close = float(row["Close"])
            continue

        pct_change = None
        if prev_close and prev_close > 0:
            pct_change = round(float(((float(row["Close"]) - prev_close) / prev_close) * 100), 4)

        db.add(PriceHistory(
            ticker_id=ticker.id,
            date=record_date,
            open=round(float(row["Open"]), 4),
            high=round(float(row["High"]), 4),
            low=round(float(row["Low"]), 4),
            close=round(float(row["Close"]), 4),
            volume=int(row["Volume"]) if row["Volume"] else None,
            pct_change=pct_change,
        ))
        added += 1
        prev_close = float(row["Close"])

    db.commit()
    return added


def main():
    db = SessionLocal()
    try:
        tickers = db.query(Ticker).order_by(Ticker.symbol).all()
        if not tickers:
            logger.info("No tickers in watchlist — nothing to fetch")
            return

        logger.info(f"Fetching prices for {len(tickers)} tickers...")
        total = 0
        for ticker in tickers:
            try:
                added = fetch_for_ticker(db, ticker)
                logger.info(f"{ticker.symbol}: +{added} new records")
                total += added
            except Exception as e:
                logger.error(f"{ticker.symbol}: Failed — {e}")

        logger.info(f"Done. Total new price records: {total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
