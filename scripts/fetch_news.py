#!/usr/bin/env python3
"""
Fetch and store daily sentiment scores for all watchlist tickers.

Run manually:
    cd edgeboard/backend
    source .venv/bin/activate
    PYTHONPATH=. python ../scripts/fetch_news.py

Runs automatically via launchd every weekday morning (see scripts/install_jobs.sh)
"""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.db.database import SessionLocal
from app.models.ticker import Ticker
from app.services.sentiment_service import run_sentiment_for_ticker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    db = SessionLocal()
    try:
        tickers = db.query(Ticker).order_by(Ticker.symbol).all()
        if not tickers:
            logger.info("No tickers in watchlist — nothing to fetch")
            return

        logger.info(f"Fetching sentiment for {len(tickers)} tickers...")
        for ticker in tickers:
            try:
                stored = run_sentiment_for_ticker(db, ticker.symbol, days=1)
                logger.info(f"{ticker.symbol}: {len(stored)} new sentiment record(s)")
            except Exception as e:
                logger.error(f"{ticker.symbol}: Failed — {e}")

        logger.info("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
