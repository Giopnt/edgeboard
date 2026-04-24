from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.ticker import Ticker
from app.schemas.ticker import TickerCreate, TickerResponse, TickerList

router = APIRouter(prefix="/tickers", tags=["tickers"])


@router.get("", response_model=TickerList)
def list_tickers(db: Session = Depends(get_db)):
    """List all tracked tickers."""
    tickers = db.query(Ticker).order_by(Ticker.symbol).all()
    return TickerList(tickers=tickers, total=len(tickers))


@router.get("/{symbol}", response_model=TickerResponse)
def get_ticker(symbol: str, db: Session = Depends(get_db)):
    """Get a single ticker by symbol."""
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol.upper()).first()
    if not ticker:
        raise HTTPException(status_code=404, detail=f"Ticker {symbol.upper()} not found")
    return ticker


@router.post("", response_model=TickerResponse, status_code=status.HTTP_201_CREATED)
def create_ticker(payload: TickerCreate, db: Session = Depends(get_db)):
    """Add a ticker to the watchlist."""
    existing = db.query(Ticker).filter(Ticker.symbol == payload.symbol).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{payload.symbol} is already in your watchlist",
        )
    ticker = Ticker(**payload.model_dump())
    db.add(ticker)
    db.commit()
    db.refresh(ticker)
    return ticker


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticker(symbol: str, db: Session = Depends(get_db)):
    """Remove a ticker from the watchlist."""
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol.upper()).first()
    if not ticker:
        raise HTTPException(status_code=404, detail=f"Ticker {symbol.upper()} not found")
    db.delete(ticker)
    db.commit()
