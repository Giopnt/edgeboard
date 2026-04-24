import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.ticker import Ticker
from app.models.price import PriceHistory
from app.services.signal_service import scan_ticker
from app.services.live_radar_service import run_live_radar, RADAR_UNIVERSE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market"])

POPULAR_STOCKS = RADAR_UNIVERSE


@router.get("/popular")
def get_popular_stocks():
    """Return the curated list of popular stocks for watchlist suggestions."""
    return {"stocks": POPULAR_STOCKS}


@router.get("/radar")
def get_market_radar():
    """
    Autonomous market radar — scans 25 popular stocks via live yfinance data.
    No watchlist needed. Returns expert-language insights on whatever is
    technically interesting right now across the market.
    Takes ~5-10 seconds on first load.
    """
    return run_live_radar()


@router.get("/radar/watchlist")
def get_watchlist_radar(db: Session = Depends(get_db)):
    """
    Radar scoped to your personal watchlist only.
    Requires tickers to have price data fetched first.
    """
    tickers_with_data = (
        db.query(Ticker)
        .join(PriceHistory, Ticker.id == PriceHistory.ticker_id)
        .distinct()
        .all()
    )

    if not tickers_with_data:
        return {
            "message": "No price data. Add tickers and fetch their prices first.",
            "insights": [],
            "scanned": 0,
        }

    insights = []
    for ticker in tickers_with_data:
        try:
            scan = scan_ticker(db, ticker.symbol)
            if scan.get("signal_count", 0) == 0:
                continue
            # Reuse live radar insight generator for consistent language
            from app.services.live_radar_service import _generate_insight
            meta = {"name": ticker.name or ticker.symbol, "sector": ticker.sector or "—"}
            # Build a minimal scan dict compatible with _generate_insight
            insight = _generate_insight(scan, meta)
            if insight:
                insights.append(insight)
        except Exception as e:
            logger.error(f"Watchlist radar failed for {ticker.symbol}: {e}")

    priority_order = {"high": 0, "medium": 1, "low": 2}
    insights.sort(key=lambda x: (priority_order.get(x["priority"], 3), -x["signal_count"]))

    return {
        "scanned": len(tickers_with_data),
        "with_signals": len(insights),
        "insights": insights,
    }