from datetime import date, timedelta
from unittest.mock import patch

import pandas as pd
import pytest

from app.models.ticker import Ticker
from app.models.price import PriceHistory
from app.services.opportunity_service import (
    compute_rsi,
    compute_sma,
    compute_volume_zscore,
    detect_rsi_oversold,
    detect_rsi_overbought,
    detect_big_moves,
    detect_volume_spikes,
    _compute_outcome,
    build_price_dataframe,
)


# ── Indicator unit tests ──────────────────────────────────────────────────────

def test_compute_rsi_basic():
    closes = pd.Series([44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.15,
                        43.61, 44.33, 44.83, 45.10, 45.15, 43.61, 44.5])
    rsi = compute_rsi(closes, period=14)
    assert rsi.notna().any()
    assert (rsi.dropna() >= 0).all()
    assert (rsi.dropna() <= 100).all()


def test_compute_sma():
    closes = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    sma3 = compute_sma(closes, 3)
    assert sma3.iloc[2] == 20.0
    assert sma3.iloc[3] == 30.0


def test_compute_volume_zscore():
    volumes = pd.Series([1000.0] * 19 + [5000.0])
    zscores = compute_volume_zscore(volumes, period=20)
    assert zscores.iloc[-1] > 2.0  # Last value is a spike


def test_detect_big_moves_bullish():
    df = pd.DataFrame([
        {"date": date.today() - timedelta(days=5), "close": 100.0, "pct_change": 5.0,
         "volume": 1000, "rsi": 50.0, "sma20": 98.0, "sma50": 95.0, "volume_zscore": 1.0},
        {"date": date.today() - timedelta(days=4), "close": 102.0, "pct_change": 2.0,
         "volume": 1000, "rsi": 55.0, "sma20": 99.0, "sma50": 95.0, "volume_zscore": 0.5},
        {"date": date.today() - timedelta(days=3), "close": 104.0, "pct_change": 2.0,
         "volume": 1000, "rsi": 58.0, "sma20": 100.0, "sma50": 96.0, "volume_zscore": 0.5},
    ])
    results = detect_big_moves(df, threshold=4.0)
    assert len(results) == 1
    assert results[0]["direction"] == "bullish"
    assert results[0]["signal_type"] == "big_move"


def test_detect_big_moves_bearish():
    df = pd.DataFrame([
        {"date": date.today() - timedelta(days=2), "close": 100.0, "pct_change": -6.0,
         "volume": 1000, "rsi": 40.0, "sma20": 105.0, "sma50": 102.0, "volume_zscore": 1.5},
        {"date": date.today() - timedelta(days=1), "close": 98.0, "pct_change": -2.0,
         "volume": 1000, "rsi": 38.0, "sma20": 104.0, "sma50": 102.0, "volume_zscore": 0.5},
    ])
    results = detect_big_moves(df, threshold=4.0)
    assert len(results) == 1
    assert results[0]["direction"] == "bearish"


def test_detect_rsi_oversold():
    df = pd.DataFrame([
        {"date": date.today() - timedelta(days=3), "close": 100.0, "pct_change": -1.0,
         "rsi": 35.0, "sma20": 105.0, "sma50": 108.0, "volume": 1000, "volume_zscore": 0.5},
        {"date": date.today() - timedelta(days=2), "close": 98.0, "pct_change": -2.0,
         "rsi": 28.0, "sma20": 103.0, "sma50": 107.0, "volume": 1000, "volume_zscore": 0.5},
        {"date": date.today() - timedelta(days=1), "close": 101.0, "pct_change": 3.0,
         "rsi": 35.0, "sma20": 102.0, "sma50": 106.0, "volume": 1000, "volume_zscore": 0.5},
    ])
    results = detect_rsi_oversold(df, threshold=30.0)
    assert len(results) == 1
    assert results[0]["direction"] == "bullish"
    assert results[0]["signal_type"] == "rsi_oversold"


def test_detect_rsi_overbought():
    df = pd.DataFrame([
        {"date": date.today() - timedelta(days=3), "close": 100.0, "pct_change": 1.0,
         "rsi": 65.0, "sma20": 98.0, "sma50": 95.0, "volume": 1000, "volume_zscore": 0.5},
        {"date": date.today() - timedelta(days=2), "close": 105.0, "pct_change": 5.0,
         "rsi": 72.0, "sma20": 99.0, "sma50": 95.0, "volume": 1000, "volume_zscore": 0.5},
        {"date": date.today() - timedelta(days=1), "close": 103.0, "pct_change": -2.0,
         "rsi": 68.0, "sma20": 100.0, "sma50": 96.0, "volume": 1000, "volume_zscore": 0.5},
    ])
    results = detect_rsi_overbought(df, threshold=70.0)
    assert len(results) == 1
    assert results[0]["direction"] == "bearish"
    assert results[0]["signal_type"] == "rsi_overbought"


def test_compute_outcome_positive():
    df = pd.DataFrame([
        {"date": date.today() - timedelta(days=6), "close": 100.0, "pct_change": 0.0},
        {"date": date.today() - timedelta(days=5), "close": 100.0, "pct_change": 0.0},
        {"date": date.today() - timedelta(days=4), "close": 102.0, "pct_change": 2.0},
        {"date": date.today() - timedelta(days=3), "close": 104.0, "pct_change": 2.0},
        {"date": date.today() - timedelta(days=2), "close": 106.0, "pct_change": 2.0},
        {"date": date.today() - timedelta(days=1), "close": 110.0, "pct_change": 4.0},
    ])
    result = _compute_outcome(df, signal_idx=0, forward_days=5)
    assert result["outcome_pct"] == 10.0
    assert result["outcome_days"] == 5


def test_compute_outcome_at_end():
    df = pd.DataFrame([
        {"date": date.today(), "close": 100.0, "pct_change": 0.0},
    ])
    result = _compute_outcome(df, signal_idx=0)
    assert result["outcome_pct"] is None


# ── API integration tests ─────────────────────────────────────────────────────

def _seed_price_data(db, ticker_id: int, num_days: int = 100):
    """Helper to insert fake price data for testing."""
    base_price = 100.0
    for i in range(num_days, 0, -1):
        price = base_price + (i % 10) - 5
        prev_price = base_price + ((i + 1) % 10) - 5
        pct = round(((price - prev_price) / prev_price) * 100, 4) if prev_price else 0
        db.add(PriceHistory(
            ticker_id=ticker_id,
            date=date.today() - timedelta(days=i),
            open=price - 0.5,
            high=price + 1.0,
            low=price - 1.0,
            close=price,
            volume=1_000_000 + (i * 10000),
            pct_change=pct,
        ))
    db.commit()


def test_scan_opportunities_ticker_not_found(client):
    response = client.post("/api/opportunities/FAKE/scan")
    assert response.status_code == 404


def test_scan_opportunities_no_price_data(client, db):
    db.add(Ticker(symbol="AAPL", name="Apple"))
    db.commit()

    response = client.post("/api/opportunities/AAPL/scan")
    assert response.status_code == 200
    assert response.json()["opportunities_found"] == 0


def test_scan_and_get_past_opportunities(client, db):
    ticker = Ticker(symbol="MSFT", name="Microsoft")
    db.add(ticker)
    db.commit()
    db.refresh(ticker)

    _seed_price_data(db, ticker.id, num_days=100)

    scan = client.post("/api/opportunities/MSFT/scan?days=90")
    assert scan.status_code == 200
    found = scan.json()["opportunities_found"]

    past = client.get("/api/opportunities/MSFT/past")
    assert past.status_code == 200
    assert past.json()["total"] == found


def test_get_best_opportunities(client, db):
    ticker = Ticker(symbol="NVDA", name="NVIDIA")
    db.add(ticker)
    db.commit()
    db.refresh(ticker)

    _seed_price_data(db, ticker.id, num_days=100)

    response = client.get("/api/opportunities/NVDA/best?days=90&limit=3")
    assert response.status_code == 200
    data = response.json()
    assert "opportunities" in data
    assert len(data["opportunities"]) <= 3


def test_watchlist_summary_empty(client):
    response = client.get("/api/opportunities/watchlist/summary")
    assert response.status_code == 200
    assert response.json()["message"] == "No tickers in watchlist"


def test_past_opportunities_filter_direction(client, db):
    ticker = Ticker(symbol="TSLA", name="Tesla")
    db.add(ticker)
    db.commit()
    db.refresh(ticker)
    _seed_price_data(db, ticker.id, num_days=100)

    client.post("/api/opportunities/TSLA/scan?days=90")

    bullish = client.get("/api/opportunities/TSLA/past?direction=bullish")
    bearish = client.get("/api/opportunities/TSLA/past?direction=bearish")

    assert bullish.status_code == 200
    assert bearish.status_code == 200
    for opp in bullish.json()["opportunities"]:
        assert opp["direction"] == "bullish"
    for opp in bearish.json()["opportunities"]:
        assert opp["direction"] == "bearish"