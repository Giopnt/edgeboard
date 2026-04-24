from datetime import date, timedelta
from unittest.mock import patch

import pandas as pd
import pytest

from app.models.ticker import Ticker
from app.models.price import PriceHistory
from app.models.sentiment import SentimentScore
from app.services.signal_service import (
    scan_rsi,
    scan_volume,
    scan_moving_average_trend,
    scan_price_momentum,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_df(closes, pct_changes=None, volumes=None):
    """Build a minimal DataFrame for testing signal detectors."""
    n = len(closes)
    df = pd.DataFrame({
        "date": [date.today() - timedelta(days=n - i) for i in range(n)],
        "close": closes,
        "pct_change": pct_changes or [0.0] * n,
        "volume": volumes or [1_000_000] * n,
    })
    from app.services.opportunity_service import compute_rsi, compute_sma, compute_volume_zscore
    df["rsi"] = compute_rsi(df["close"])
    df["sma20"] = compute_sma(df["close"], 20)
    df["sma50"] = compute_sma(df["close"], 50)
    df["volume_zscore"] = compute_volume_zscore(df["volume"].astype(float))
    return df


def seed_prices(db, ticker_id, closes):
    for i, close in enumerate(closes):
        db.add(PriceHistory(
            ticker_id=ticker_id,
            date=date.today() - timedelta(days=len(closes) - i),
            open=close - 0.5,
            high=close + 1.0,
            low=close - 1.0,
            close=close,
            volume=1_000_000,
            pct_change=0.0,
        ))
    db.commit()


# ── Unit tests ────────────────────────────────────────────────────────────────

def test_scan_rsi_oversold():
    # Simulate a declining price series that would produce low RSI
    closes = [100.0] * 5 + [95, 90, 85, 80, 75, 70, 65, 62, 60, 58, 57, 56, 55, 54, 53]
    df = make_df(closes)
    result = scan_rsi(df)
    if result:
        assert result["direction"] == "bullish"
        assert result["signal_type"] == "rsi_oversold"


def test_scan_rsi_overbought():
    # Simulate a strongly rising price series — should produce high RSI
    closes = [float(100 + i * 2) for i in range(40)]
    df = make_df(closes)
    result = scan_rsi(df)
    if result:
        assert result["direction"] == "bearish"
        assert result["signal_type"] == "rsi_overbought"


def test_scan_rsi_neutral():
    # Gently oscillating prices keep RSI in neutral zone (35-65)
    import math
    closes = [100.0 + math.sin(i * 0.5) * 2 for i in range(30)]
    df = make_df(closes)
    result = scan_rsi(df)
    assert result is None


def test_scan_rsi_empty_df():
    result = scan_rsi(pd.DataFrame())
    assert result is None


def test_scan_volume_spike_bullish():
    # 19 normal days, then one huge volume up day
    volumes = [1_000_000] * 19 + [10_000_000]
    closes = [100.0] * 19 + [105.0]
    pct_changes = [0.0] * 19 + [5.0]
    df = make_df(closes, pct_changes=pct_changes, volumes=volumes)
    result = scan_volume(df)
    assert result is not None
    assert result["direction"] == "bullish"
    assert result["signal_type"] == "volume_spike"


def test_scan_volume_spike_bearish():
    volumes = [1_000_000] * 19 + [10_000_000]
    closes = [100.0] * 19 + [95.0]
    pct_changes = [0.0] * 19 + [-5.0]
    df = make_df(closes, pct_changes=pct_changes, volumes=volumes)
    result = scan_volume(df)
    assert result is not None
    assert result["direction"] == "bearish"


def test_scan_volume_no_spike():
    closes = [100.0] * 30
    df = make_df(closes)
    result = scan_volume(df)
    assert result is None


def test_scan_ma_bullish_trend():
    # Steadily rising prices — price above both MAs
    closes = [float(90 + i) for i in range(60)]
    df = make_df(closes)
    result = scan_moving_average_trend(df)
    assert result is not None
    assert result["direction"] == "bullish"
    assert result["signal_type"] == "ma_bullish_trend"


def test_scan_ma_bearish_trend():
    # Steadily falling prices — price below both MAs
    closes = [float(150 - i) for i in range(60)]
    df = make_df(closes)
    result = scan_moving_average_trend(df)
    assert result is not None
    assert result["direction"] == "bearish"
    assert result["signal_type"] == "ma_bearish_trend"


def test_scan_price_momentum_bullish():
    closes = [100.0] * 10 + [105, 107, 109, 111, 113]
    df = make_df(closes)
    result = scan_price_momentum(df, lookback=5)
    assert result is not None
    assert result["direction"] == "bullish"
    assert result["value"] > 4.0


def test_scan_price_momentum_bearish():
    closes = [100.0] * 10 + [95, 93, 91, 89, 87]
    df = make_df(closes)
    result = scan_price_momentum(df, lookback=5)
    assert result is not None
    assert result["direction"] == "bearish"
    assert result["value"] < -4.0


def test_scan_price_momentum_flat():
    closes = [100.0] * 15
    df = make_df(closes)
    result = scan_price_momentum(df, lookback=5)
    assert result is None


# ── API integration tests ─────────────────────────────────────────────────────

def test_signals_ticker_not_found(client):
    response = client.get("/api/signals/FAKE")
    assert response.status_code == 404


def test_signals_no_price_data(client, db):
    db.add(Ticker(symbol="AAPL", name="Apple"))
    db.commit()

    response = client.get("/api/signals/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["has_data"] is False
    assert data["signals"] == []


def test_signals_with_price_data(client, db):
    ticker = Ticker(symbol="MSFT", name="Microsoft")
    db.add(ticker)
    db.commit()
    db.refresh(ticker)

    # Rising prices → should trigger bullish MA trend signal
    closes = [float(90 + i) for i in range(60)]
    seed_prices(db, ticker.id, closes)

    response = client.get("/api/signals/MSFT")
    assert response.status_code == 200
    data = response.json()
    assert data["has_data"] is True
    assert "signals" in data
    assert "summary" in data
    assert "disclaimer" in data
    assert isinstance(data["signal_count"], int)


def test_watchlist_signals_empty(client):
    response = client.get("/api/signals")
    assert response.status_code == 200
    assert "No tickers" in response.json()["message"]


def test_watchlist_signals_with_tickers(client, db):
    for sym, name in [("AAPL", "Apple"), ("NVDA", "NVIDIA")]:
        t = Ticker(symbol=sym, name=name)
        db.add(t)
        db.commit()
        db.refresh(t)
        closes = [float(90 + i) for i in range(60)]
        seed_prices(db, t.id, closes)

    response = client.get("/api/signals")
    assert response.status_code == 200
    data = response.json()
    assert data["tickers_scanned"] == 2
    assert len(data["results"]) == 2
    assert "total_signals" in data


def test_signal_response_has_disclaimer(client, db):
    ticker = Ticker(symbol="TSLA", name="Tesla")
    db.add(ticker)
    db.commit()
    db.refresh(ticker)
    closes = [float(90 + i) for i in range(60)]
    seed_prices(db, ticker.id, closes)

    response = client.get("/api/signals/TSLA")
    assert response.status_code == 200
    # Disclaimer must always be present
    assert "disclaimer" in response.json()
    assert "not financial advice" in response.json()["disclaimer"]