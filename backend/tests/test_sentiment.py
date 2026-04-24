from datetime import date, timedelta
from unittest.mock import patch

from app.models.ticker import Ticker
from app.models.sentiment import SentimentScore
from app.services.sentiment_service import score_headlines, compute_trend, store_sentiment


# ── Unit tests for the sentiment service ─────────────────────────────────────

def test_score_headlines_positive():
    headlines = [
        "Apple reports record profits, stock surges to all-time high",
        "Strong earnings beat crushes expectations, investors celebrate",
    ]
    scores = score_headlines(headlines)
    assert scores["compound"] > 0.05  # Should be bullish


def test_score_headlines_negative():
    headlines = [
        "Stock crashes amid fraud allegations and regulatory crackdown",
        "Company misses earnings badly, layoffs announced",
    ]
    scores = score_headlines(headlines)
    assert scores["compound"] < -0.05  # Should be bearish


def test_score_headlines_empty():
    scores = score_headlines([])
    assert scores["compound"] == 0.0
    assert scores["neu"] == 1.0


def test_compute_trend_improving():
    scores = [-0.3, -0.2, -0.1, 0.1, 0.2, 0.3]
    assert compute_trend(scores) == "improving"


def test_compute_trend_worsening():
    scores = [0.3, 0.2, 0.1, -0.1, -0.2, -0.3]
    assert compute_trend(scores) == "worsening"


def test_compute_trend_stable():
    scores = [0.1, 0.05, 0.1, 0.08, 0.09, 0.1]
    assert compute_trend(scores) == "stable"


def test_compute_trend_too_short():
    assert compute_trend([0.1]) == "stable"


# ── API integration tests ─────────────────────────────────────────────────────

def test_sentiment_history_not_found(client):
    response = client.get("/api/sentiment/FAKE")
    assert response.status_code == 404


def test_sentiment_history_empty(client, db):
    db.add(Ticker(symbol="GOOGL", name="Alphabet"))
    db.commit()

    response = client.get("/api/sentiment/GOOGL")
    assert response.status_code == 200
    assert response.json() == []


def test_sentiment_summary_no_data(client, db):
    db.add(Ticker(symbol="META", name="Meta"))
    db.commit()

    response = client.get("/api/sentiment/META/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "META"
    assert data["latest_score"] is None
    assert data["avg_score_7d"] is None


def test_sentiment_fetch_no_api_key(client, db):
    """When NEWS_API_KEY is empty, fetch returns 0 records (no crash)."""
    db.add(Ticker(symbol="AMZN", name="Amazon"))
    db.commit()

    with patch("app.services.sentiment_service.settings") as mock_settings:
        mock_settings.news_api_key = ""  # Simulate no key
        response = client.post("/api/sentiment/AMZN/fetch?days=1")

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AMZN"
    assert data["records_stored"] == 1  # Still stores record, just with 0 headlines


def test_sentiment_history_returns_data(client, db):
    """Manually insert a sentiment record and verify the endpoint returns it."""
    ticker = Ticker(symbol="NFLX", name="Netflix")
    db.add(ticker)
    db.commit()
    db.refresh(ticker)

    record = SentimentScore(
        ticker_id=ticker.id,
        date=date.today(),
        compound_score=0.42,
        positive=0.3,
        neutral=0.6,
        negative=0.1,
        headline_count=5,
        label="bullish",
    )
    db.add(record)
    db.commit()

    response = client.get("/api/sentiment/NFLX?days=7")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["compound_score"] == 0.42
    assert data[0]["label"] == "bullish"


def test_sentiment_summary_with_data(client, db):
    """Insert records and verify summary computes correctly."""
    ticker = Ticker(symbol="AMD", name="AMD")
    db.add(ticker)
    db.commit()
    db.refresh(ticker)

    for i in range(7):
        db.add(SentimentScore(
            ticker_id=ticker.id,
            date=date.today() - timedelta(days=i),
            compound_score=0.2,
            positive=0.3,
            neutral=0.6,
            negative=0.1,
            headline_count=3,
            label="bullish",
        ))
    db.commit()

    response = client.get("/api/sentiment/AMD/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["avg_score_7d"] is not None
    assert data["latest_label"] == "bullish"
    assert data["trend"] in ("improving", "worsening", "stable")