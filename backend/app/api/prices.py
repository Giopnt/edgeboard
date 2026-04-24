from datetime import date, timedelta

import yfinance as yf
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.ticker import Ticker
from app.models.price import PriceHistory
from app.schemas.price import PriceResponse, PriceFetchResponse

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("/{symbol}", response_model=list[PriceResponse])
def get_prices(
    symbol: str,
    days: int = Query(default=90, ge=1, le=365 * 5),
    db: Session = Depends(get_db),
):
    """Get price history for a ticker."""
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol.upper()).first()
    if not ticker:
        raise HTTPException(status_code=404, detail=f"Ticker {symbol.upper()} not found")

    since = date.today() - timedelta(days=days)
    prices = (
        db.query(PriceHistory)
        .filter(PriceHistory.ticker_id == ticker.id, PriceHistory.date >= since)
        .order_by(PriceHistory.date.asc())
        .all()
    )
    return prices


@router.post("/{symbol}/fetch", response_model=PriceFetchResponse)
def fetch_prices(
    symbol: str,
    days: int = Query(default=365, ge=1, le=365 * 5),
    db: Session = Depends(get_db),
):
    """
    Fetch latest price data from yfinance and store in DB.
    Safe to call multiple times — skips dates already stored.
    """
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol.upper()).first()
    if not ticker:
        raise HTTPException(status_code=404, detail=f"Ticker {symbol.upper()} not found")

    yf_ticker = yf.Ticker(symbol.upper())
    hist = yf_ticker.history(period=f"{days}d")

    if hist.empty:
        raise HTTPException(status_code=502, detail=f"No data returned from yfinance for {symbol.upper()}")

    existing_dates = {
        row.date
        for row in db.query(PriceHistory.date)
        .filter(PriceHistory.ticker_id == ticker.id)
        .all()
    }

    records_added = 0
    prev_close = None

    for ts, row in hist.iterrows():
        record_date = ts.date()
        if record_date in existing_dates:
            prev_close = float(row["Close"])
            continue

        pct_change = None
        if prev_close is not None and prev_close > 0:
            pct_change = round(float(((float(row["Close"]) - prev_close) / prev_close) * 100), 4)

        price = PriceHistory(
            ticker_id=ticker.id,
            date=record_date,
            open=round(float(row["Open"]), 4),
            high=round(float(row["High"]), 4),
            low=round(float(row["Low"]), 4),
            close=round(float(row["Close"]), 4),
            volume=int(row["Volume"]) if row["Volume"] else None,
            pct_change=pct_change,
        )
        db.add(price)
        records_added += 1
        prev_close = float(row["Close"])

    db.commit()

    dates = hist.index
    return PriceFetchResponse(
        symbol=symbol.upper(),
        records_added=records_added,
        date_from=dates[0].date() if len(dates) else None,
        date_to=dates[-1].date() if len(dates) else None,
        message=f"Added {records_added} new price records for {symbol.upper()}",
    )