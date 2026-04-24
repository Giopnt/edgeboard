import json
import logging
from datetime import date, timedelta

import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ticker import Ticker
from app.models.sentiment import SentimentScore

logger = logging.getLogger(__name__)

analyzer = SentimentIntensityAnalyzer()


def _score_label(compound: float) -> str:
    """Convert VADER compound score to human-readable label."""
    if compound >= 0.05:
        return "bullish"
    elif compound <= -0.05:
        return "bearish"
    return "neutral"


def fetch_headlines(symbol: str, from_date: date, to_date: date) -> list[str]:
    """
    Fetch news headlines for a ticker from NewsAPI.
    Returns list of headline strings.
    """
    if not settings.news_api_key:
        logger.warning("NEWS_API_KEY not set — skipping headline fetch")
        return []

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": symbol,
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
        "language": "en",
        "sortBy": "relevancy",
        "pageSize": 30,
        "apiKey": settings.news_api_key,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        articles = data.get("articles", [])
        headlines = [
            a["title"]
            for a in articles
            if a.get("title") and "[Removed]" not in a["title"]
        ]
        logger.info(f"Fetched {len(headlines)} headlines for {symbol}")
        return headlines
    except requests.RequestException as e:
        logger.error(f"NewsAPI request failed for {symbol}: {e}")
        return []


def score_headlines(headlines: list[str]) -> dict:
    """
    Run VADER sentiment analysis on a list of headlines.
    Returns averaged scores across all headlines.
    """
    if not headlines:
        return {"compound": 0.0, "pos": 0.0, "neu": 1.0, "neg": 0.0}

    totals = {"compound": 0.0, "pos": 0.0, "neu": 0.0, "neg": 0.0}
    for headline in headlines:
        scores = analyzer.polarity_scores(headline)
        for key in totals:
            totals[key] += scores[key]

    count = len(headlines)
    return {k: round(v / count, 4) for k, v in totals.items()}


def store_sentiment(
    db: Session,
    ticker: Ticker,
    target_date: date,
    headlines: list[str],
    scores: dict,
) -> SentimentScore:
    """
    Upsert a SentimentScore record for a ticker on a given date.
    Safe to call multiple times — updates if already exists.
    """
    existing = (
        db.query(SentimentScore)
        .filter(
            SentimentScore.ticker_id == ticker.id,
            SentimentScore.date == target_date,
        )
        .first()
    )

    label = _score_label(scores["compound"])

    if existing:
        existing.compound_score = scores["compound"]
        existing.positive = scores["pos"]
        existing.neutral = scores["neu"]
        existing.negative = scores["neg"]
        existing.headline_count = len(headlines)
        existing.label = label
        existing.headlines_json = json.dumps(headlines[:10])  # Store top 10
        db.commit()
        db.refresh(existing)
        return existing

    record = SentimentScore(
        ticker_id=ticker.id,
        date=target_date,
        compound_score=scores["compound"],
        positive=scores["pos"],
        neutral=scores["neu"],
        negative=scores["neg"],
        headline_count=len(headlines),
        label=label,
        headlines_json=json.dumps(headlines[:10]),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def run_sentiment_for_ticker(db: Session, symbol: str, days: int = 7) -> list[SentimentScore]:
    """
    Fetch + score + store sentiment for a ticker over the last N days.
    Skips dates that already have records.
    Returns list of stored SentimentScore records.
    """
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol.upper()).first()
    if not ticker:
        raise ValueError(f"Ticker {symbol} not found in DB")

    existing_dates = {
        row.date
        for row in db.query(SentimentScore.date)
        .filter(SentimentScore.ticker_id == ticker.id)
        .all()
    }

    stored = []
    today = date.today()

    for i in range(days):
        target_date = today - timedelta(days=i)
        if target_date in existing_dates:
            logger.info(f"Sentiment already exists for {symbol} on {target_date} — skipping")
            continue

        headlines = fetch_headlines(symbol, from_date=target_date, to_date=target_date)
        scores = score_headlines(headlines)
        record = store_sentiment(db, ticker, target_date, headlines, scores)
        stored.append(record)
        logger.info(f"Stored sentiment for {symbol} on {target_date}: {record.label} ({record.compound_score})")

    return stored


def compute_trend(scores: list[float]) -> str:
    """
    Given a list of compound scores ordered oldest → newest,
    return 'improving', 'worsening', or 'stable'.
    """
    if len(scores) < 2:
        return "stable"
    avg_first_half = sum(scores[: len(scores) // 2]) / (len(scores) // 2)
    avg_second_half = sum(scores[len(scores) // 2 :]) / (len(scores) - len(scores) // 2)
    diff = avg_second_half - avg_first_half
    if diff > 0.05:
        return "improving"
    elif diff < -0.05:
        return "worsening"
    return "stable"