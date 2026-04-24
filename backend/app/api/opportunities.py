from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.ticker import Ticker
from app.models.signal import Signal
from app.services.opportunity_service import (
    run_opportunity_scan,
    get_best_missed_opportunities,
)

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def _signal_to_dict(s: Signal) -> dict:
    """Serialize a Signal to a dict using signal_date if available."""
    date_str = (
        s.signal_date.isoformat()
        if s.signal_date
        else s.created_at.date().isoformat()
    )
    return {
        "id": s.id,
        "date": date_str,
        "signal_type": s.signal_type,
        "direction": s.direction,
        "strength": s.strength,
        "description": s.description,
        "outcome_pct": s.outcome_pct,
        "outcome_days": int(s.outcome_days) if s.outcome_days is not None else None,
    }


@router.post("/{symbol}/scan")
def scan_opportunities(
    symbol: str,
    days: int = Query(default=365, ge=30, le=365 * 3),
    db: Session = Depends(get_db),
):
    """
    Scan a ticker's price history for past opportunities.
    Detects: RSI crossings, volume spikes, golden/death cross, big moves.
    """
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol.upper()).first()
    if not ticker:
        raise HTTPException(status_code=404, detail=f"Ticker {symbol.upper()} not found")

    try:
        opportunities = run_opportunity_scan(db, symbol.upper(), days=days, store=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "symbol": symbol.upper(),
        "opportunities_found": len(opportunities),
        "days_scanned": days,
        "message": f"Found {len(opportunities)} past opportunities for {symbol.upper()} over {days} days",
    }


@router.get("/{symbol}/past")
def get_past_opportunities(
    symbol: str,
    days: int = Query(default=90, ge=7, le=365 * 3),
    signal_type: str | None = Query(default=None),
    direction: str | None = Query(default=None, pattern="^(bullish|bearish)$"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Get historical past opportunities for a ticker."""
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol.upper()).first()
    if not ticker:
        raise HTTPException(status_code=404, detail=f"Ticker {symbol.upper()} not found")

    query = (
        db.query(Signal)
        .filter(Signal.ticker_id == ticker.id, Signal.is_past_opportunity == True)  # noqa
    )
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    if direction:
        query = query.filter(Signal.direction == direction)

    signals = query.order_by(Signal.signal_date.desc().nullslast(), Signal.created_at.desc()).limit(limit).all()

    return {
        "symbol": symbol.upper(),
        "total": len(signals),
        "opportunities": [_signal_to_dict(s) for s in signals],
    }


@router.get("/{symbol}/best")
def get_best_opportunities(
    symbol: str,
    days: int = Query(default=90, ge=7, le=365),
    limit: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Get top N biggest missed opportunities ranked by absolute outcome.
    Use ?limit=10 for top 10, ?limit=1 for top 1, etc.
    """
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol.upper()).first()
    if not ticker:
        raise HTTPException(status_code=404, detail=f"Ticker {symbol.upper()} not found")

    try:
        opportunities = get_best_missed_opportunities(db, symbol.upper(), days=days, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not opportunities:
        return {
            "symbol": symbol.upper(),
            "message": "No price data found. Fetch prices first via POST /api/prices/{symbol}/fetch",
            "opportunities": [],
        }

    return {
        "symbol": symbol.upper(),
        "days_analyzed": days,
        "total": len(opportunities),
        "opportunities": opportunities,
    }


@router.get("/watchlist/summary")
def get_watchlist_opportunities(
    days: int = Query(default=30, ge=7, le=365),
    db: Session = Depends(get_db),
):
    """Scan all tracked tickers and return the biggest missed opportunity per ticker."""
    tickers = db.query(Ticker).order_by(Ticker.symbol).all()
    if not tickers:
        return {"message": "No tickers in watchlist", "summary": []}

    summary = []
    for ticker in tickers:
        try:
            best = get_best_missed_opportunities(db, ticker.symbol, days=days, limit=1)
            summary.append({
                "symbol": ticker.symbol,
                "best_opportunity": best[0] if best else None,
            })
        except Exception as e:
            summary.append({"symbol": ticker.symbol, "error": str(e)})

    summary.sort(
        key=lambda x: abs(x["best_opportunity"]["outcome_pct"])
        if x.get("best_opportunity") and x["best_opportunity"].get("outcome_pct")
        else 0,
        reverse=True,
    )
    return {"days_analyzed": days, "total_tickers": len(tickers), "summary": summary}