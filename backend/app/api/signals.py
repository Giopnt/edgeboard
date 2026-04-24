from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.ticker import Ticker
from app.services.signal_service import scan_ticker, scan_watchlist

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/{symbol}")
def get_signals_for_ticker(symbol: str, db: Session = Depends(get_db)):
    """
    Scan a single ticker for active forward-looking signals.
    Checks: RSI extremes, volume spikes, MA trend, price momentum, sentiment divergence.
    Clearly labeled as pattern-based signals — not predictions.
    """
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol.upper()).first()
    if not ticker:
        raise HTTPException(
            status_code=404,
            detail=f"{symbol.upper()} not found. Add it via POST /api/tickers first.",
        )

    try:
        return scan_ticker(db, symbol.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
def get_watchlist_signals(db: Session = Depends(get_db)):
    """
    Scan every ticker in your watchlist for active signals.
    Returns results sorted by signal count — most active tickers first.
    Perfect for a morning overview: open this and see what's setting up today.
    """
    tickers = db.query(Ticker).all()
    if not tickers:
        return {
            "message": "No tickers in watchlist. Add some via POST /api/tickers first.",
            "results": [],
        }

    results = scan_watchlist(db)
    total_signals = sum(r.get("signal_count", 0) for r in results)

    return {
        "tickers_scanned": len(results),
        "total_signals": total_signals,
        "results": results,
    }