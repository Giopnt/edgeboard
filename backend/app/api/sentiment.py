from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.models.ticker import Ticker
from app.models.sentiment import SentimentScore
from app.schemas.sentiment import SentimentResponse, SentimentSummary
from app.services.sentiment_service import run_sentiment_for_ticker, compute_trend

router = APIRouter(prefix="/sentiment", tags=["sentiment"])


@router.get("/{symbol}", response_model=list[SentimentResponse])
def get_sentiment_history(
    symbol: str,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """
    Get daily sentiment history for a ticker.
    Returns one record per day, ordered newest first.
    """
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol.upper()).first()
    if not ticker:
        raise HTTPException(status_code=404, detail=f"Ticker {symbol.upper()} not found")

    since = date.today() - timedelta(days=days)
    records = (
        db.query(SentimentScore)
        .filter(SentimentScore.ticker_id == ticker.id, SentimentScore.date >= since)
        .order_by(SentimentScore.date.desc())
        .all()
    )
    return records


@router.get("/{symbol}/summary", response_model=SentimentSummary)
def get_sentiment_summary(symbol: str, db: Session = Depends(get_db)):
    """
    Aggregated sentiment summary for a ticker.
    Returns 7-day avg, 30-day avg, latest score, and trend direction.
    """
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol.upper()).first()
    if not ticker:
        raise HTTPException(status_code=404, detail=f"Ticker {symbol.upper()} not found")

    today = date.today()

    def avg_score(days: int) -> float | None:
        since = today - timedelta(days=days)
        result = (
            db.query(func.avg(SentimentScore.compound_score))
            .filter(SentimentScore.ticker_id == ticker.id, SentimentScore.date >= since)
            .scalar()
        )
        return round(float(result), 4) if result is not None else None

    latest = (
        db.query(SentimentScore)
        .filter(SentimentScore.ticker_id == ticker.id)
        .order_by(SentimentScore.date.desc())
        .first()
    )

    recent = (
        db.query(SentimentScore)
        .filter(
            SentimentScore.ticker_id == ticker.id,
            SentimentScore.date >= today - timedelta(days=14),
        )
        .order_by(SentimentScore.date.asc())
        .all()
    )
    trend = compute_trend([r.compound_score for r in recent])

    return SentimentSummary(
        symbol=symbol.upper(),
        avg_score_7d=avg_score(7),
        avg_score_30d=avg_score(30),
        latest_label=latest.label if latest else None,
        latest_score=latest.compound_score if latest else None,
        latest_date=latest.date if latest else None,
        trend=trend,
    )


@router.post("/{symbol}/fetch")
def fetch_sentiment(
    symbol: str,
    days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """
    Trigger a sentiment fetch for a ticker.
    Pulls headlines from NewsAPI, scores with VADER, stores results.
    Safe to call multiple times - skips dates already stored.
    """
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol.upper()).first()
    if not ticker:
        raise HTTPException(status_code=404, detail=f"Ticker {symbol.upper()} not found")

    try:
        stored = run_sentiment_for_ticker(db, symbol.upper(), days=days)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "symbol": symbol.upper(),
        "records_stored": len(stored),
        "message": f"Stored {len(stored)} new sentiment records for {symbol.upper()}",
    }


@router.get("/{symbol}/headlines")
def get_headlines(
    symbol: str,
    days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """
    Get stored raw headlines for a ticker (last N days).
    Useful for debugging what the sentiment is actually based on.
    """
    import json

    ticker = db.query(Ticker).filter(Ticker.symbol == symbol.upper()).first()
    if not ticker:
        raise HTTPException(status_code=404, detail=f"Ticker {symbol.upper()} not found")

    since = date.today() - timedelta(days=days)
    records = (
        db.query(SentimentScore)
        .filter(SentimentScore.ticker_id == ticker.id, SentimentScore.date >= since)
        .order_by(SentimentScore.date.desc())
        .all()
    )

    result = []
    for r in records:
        headlines = json.loads(r.headlines_json) if r.headlines_json else []
        result.append({
            "date": r.date.isoformat(),
            "label": r.label,
            "compound_score": r.compound_score,
            "headlines": headlines,
        })
    return result