import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.ticker import Ticker
from app.models.price import PriceHistory
from app.services.signal_service import scan_ticker
from app.services.live_radar_service import run_live_radar, RADAR_UNIVERSE, _generate_insight
from app.services.search_service import search_stocks, live_scan_symbol

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market"])

POPULAR_STOCKS = RADAR_UNIVERSE


@router.get("/popular")
def get_popular_stocks():
    """Return the curated list of popular stocks for watchlist suggestions."""
    return {"stocks": POPULAR_STOCKS}


@router.get("/search")
def search_any_stock(q: str = Query(..., min_length=1, description="Stock name or ticker")):
    """
    Search for any stock worldwide by name or ticker symbol.
    International stocks use exchange suffix:
      BGEO.L  = London Stock Exchange
      SAP.DE  = Frankfurt (XETRA)
      MC.PA   = Paris (Euronext)
      7203.T  = Tokyo Stock Exchange
      RELIANCE.NS = India NSE
    """
    results = search_stocks(q)
    return {
        "query": q,
        "results": results,
        "count": len(results),
        "tip": "For international stocks use suffix: .L (London), .DE (Frankfurt), .PA (Paris), .T (Tokyo), .NS (India)",
    }


@router.get("/scan/{symbol}")
def scan_any_symbol(symbol: str):
    """
    Run full signal detection on ANY stock ticker — live, no watchlist needed.
    Works for international stocks (BGEO.L, SAP.DE, MC.PA, etc.)
    Takes a few seconds to fetch live data.
    """
    return live_scan_symbol(symbol)


@router.get("/radar")
def get_market_radar():
    """
    Autonomous market radar — scans 25 popular stocks via live yfinance data.
    No watchlist needed. Returns expert-language insights on active setups.
    """
    return run_live_radar()


@router.get("/radar/watchlist")
def get_watchlist_radar(db: Session = Depends(get_db)):
    """Radar scoped to your personal watchlist only."""
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
            meta = {"name": ticker.name or ticker.symbol, "sector": ticker.sector or "—"}
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
