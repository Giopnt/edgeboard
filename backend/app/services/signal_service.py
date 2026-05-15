import logging
from datetime import date, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from app.models.ticker import Ticker
from app.models.price import PriceHistory
from app.models.sentiment import SentimentScore
from app.services.opportunity_service import (
    compute_rsi,
    compute_sma,
    compute_volume_zscore,
    build_price_dataframe,
)

logger = logging.getLogger(__name__)


# ── Individual signal detectors ───────────────────────────────────────────────

def scan_rsi(df: pd.DataFrame) -> dict | None:
    """
    Check if RSI is currently in an extreme zone.
    Returns a signal if RSI < 35 (oversold) or > 65 (overbought).
    """
    if df.empty or "rsi" not in df.columns:
        return None

    latest = df.iloc[-1]
    rsi = latest.get("rsi")
    if pd.isna(rsi):
        return None

    if rsi < 40:
        severity = "strong" if rsi < 30 else "moderate"
        return {
            "signal_type": "rsi_oversold",
            "direction": "bullish",
            "strength": round(float((35 - rsi) / 35), 4),
            "description": (
                f"RSI is currently {rsi:.1f} — oversold territory ({severity}). "
                f"Historically, readings below 35 often precede a bounce."
            ),
            "value": round(float(rsi), 2),
        }

    if rsi > 60:
        severity = "strong" if rsi > 70 else "moderate"
        return {
            "signal_type": "rsi_overbought",
            "direction": "bearish",
            "strength": round(float((rsi - 65) / 35), 4),
            "description": (
                f"RSI is currently {rsi:.1f} — overbought territory ({severity}). "
                f"Historically, readings above 65 often precede a pullback."
            ),
            "value": round(float(rsi), 2),
        }

    return None


def scan_volume(df: pd.DataFrame) -> dict | None:
    """
    Check if today's volume is unusually high (2+ standard deviations above mean).
    High volume on a move often signals conviction and continuation.
    """
    if df.empty or "volume_zscore" not in df.columns:
        return None

    latest = df.iloc[-1]
    zscore = latest.get("volume_zscore")
    pct_change = latest.get("pct_change", 0)

    if pd.isna(zscore) or zscore < 1.5:
        return None

    direction = "bullish" if (pct_change or 0) >= 0 else "bearish"
    return {
        "signal_type": "volume_spike",
        "direction": direction,
        "strength": round(float(min(zscore / 5.0, 1.0)), 4),
        "description": (
            f"Volume is {zscore:.1f} standard deviations above the 20-day average "
            f"on a {'+' if direction == 'bullish' else ''}{pct_change:.2f}% day — "
            f"unusual activity, watch for continuation."
        ),
        "value": round(float(zscore), 2),
    }


def scan_moving_average_trend(df: pd.DataFrame) -> dict | None:
    """
    Check the relationship between price and its moving averages.
    Price above both SMAs = bullish trend. Below both = bearish.
    """
    if df.empty or "sma20" not in df.columns or "sma50" not in df.columns:
        return None

    latest = df.iloc[-1]
    price = latest.get("close")
    sma20 = latest.get("sma20")
    sma50 = latest.get("sma50")

    if any(pd.isna(v) for v in [price, sma20, sma50]):
        return None

    price, sma20, sma50 = float(price), float(sma20), float(sma50)

    if price > sma20 > sma50:
        pct_above = round(((price - sma50) / sma50) * 100, 2)
        return {
            "signal_type": "ma_bullish_trend",
            "direction": "bullish",
            "strength": round(min(pct_above / 10.0, 1.0), 4),
            "description": (
                f"Price (${price:.2f}) is above both 20-day SMA (${sma20:.2f}) "
                f"and 50-day SMA (${sma50:.2f}) — bullish trend alignment. "
                f"{pct_above:.1f}% above the 50-day."
            ),
            "value": pct_above,
        }

    if price < sma20 < sma50:
        pct_below = round(((sma50 - price) / sma50) * 100, 2)
        return {
            "signal_type": "ma_bearish_trend",
            "direction": "bearish",
            "strength": round(min(pct_below / 10.0, 1.0), 4),
            "description": (
                f"Price (${price:.2f}) is below both 20-day SMA (${sma20:.2f}) "
                f"and 50-day SMA (${sma50:.2f}) — bearish trend alignment. "
                f"{pct_below:.1f}% below the 50-day."
            ),
            "value": pct_below,
        }

    return None


def scan_price_momentum(df: pd.DataFrame, lookback: int = 5) -> dict | None:
    """
    Check short-term price momentum — how much has the stock moved in last N days.
    Strong recent momentum (>5%) is worth flagging.
    """
    if len(df) < lookback + 1:
        return None

    latest_close = float(df.iloc[-1]["close"])
    past_close = float(df.iloc[-lookback]["close"])

    if past_close <= 0:
        return None

    momentum_pct = round(((latest_close - past_close) / past_close) * 100, 2)

    if abs(momentum_pct) < 3.0:
        return None

    direction = "bullish" if momentum_pct > 0 else "bearish"
    return {
        "signal_type": "price_momentum",
        "direction": direction,
        "strength": round(float(min(abs(momentum_pct) / 15.0, 1.0)), 4),
        "description": (
            f"Stock has moved {momentum_pct:+.2f}% over the last {lookback} trading days "
            f"(from ${past_close:.2f} to ${latest_close:.2f}) — "
            f"{'strong bullish' if momentum_pct > 0 else 'strong bearish'} short-term momentum."
        ),
        "value": momentum_pct,
    }


def scan_sentiment_divergence(
    df: pd.DataFrame,
    db: Session,
    ticker_id: int,
) -> dict | None:
    """
    Check if sentiment and price are moving in opposite directions.
    Bullish divergence: price falling but sentiment improving = potential reversal.
    Bearish divergence: price rising but sentiment worsening = potential top.
    """
    today = date.today()
    recent_sentiment = (
        db.query(SentimentScore)
        .filter(
            SentimentScore.ticker_id == ticker_id,
            SentimentScore.date >= today - timedelta(days=7),
        )
        .order_by(SentimentScore.date.asc())
        .all()
    )

    if len(recent_sentiment) < 2 or len(df) < 5:
        return None

    # Price trend: last 5 days
    price_change = float(df.iloc[-1]["close"]) - float(df.iloc[-5]["close"])

    # Sentiment trend: first half vs second half of recent scores
    scores = [s.compound_score for s in recent_sentiment]
    mid = len(scores) // 2
    sentiment_change = sum(scores[mid:]) / len(scores[mid:]) - sum(scores[:mid]) / len(scores[:mid])

    # Divergence: price and sentiment moving in opposite directions
    if price_change < 0 and sentiment_change > 0.05:
        return {
            "signal_type": "sentiment_divergence",
            "direction": "bullish",
            "strength": round(float(min(abs(sentiment_change), 1.0)), 4),
            "description": (
                f"Price is falling but sentiment is improving — "
                f"bullish divergence. Sentiment trend: {sentiment_change:+.3f}. "
                f"This sometimes precedes a price reversal upward."
            ),
            "value": round(float(sentiment_change), 4),
        }

    if price_change > 0 and sentiment_change < -0.05:
        return {
            "signal_type": "sentiment_divergence",
            "direction": "bearish",
            "strength": round(float(min(abs(sentiment_change), 1.0)), 4),
            "description": (
                f"Price is rising but sentiment is worsening — "
                f"bearish divergence. Sentiment trend: {sentiment_change:+.3f}. "
                f"This sometimes precedes a price reversal downward."
            ),
            "value": round(float(sentiment_change), 4),
        }

    return None


# ── Main scanner ──────────────────────────────────────────────────────────────

def scan_ticker(db: Session, symbol: str) -> dict:
    """
    Run all signal detectors on a single ticker.
    Returns a dict with all active signals and a summary.
    """
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol.upper()).first()
    if not ticker:
        raise ValueError(f"Ticker {symbol} not found")

    df = build_price_dataframe(db, ticker.id, days=120)

    if df.empty:
        return {
            "symbol": symbol.upper(),
            "has_data": False,
            "signals": [],
            "summary": "No price data. Fetch prices first via POST /api/prices/{symbol}/fetch",
        }

    latest = df.iloc[-1]
    signals = []

    # Run all detectors
    for detector in [
        lambda: scan_rsi(df),
        lambda: scan_volume(df),
        lambda: scan_moving_average_trend(df),
        lambda: scan_price_momentum(df),
        lambda: scan_sentiment_divergence(df, db, ticker.id),
    ]:
        try:
            result = detector()
            if result:
                result["symbol"] = symbol.upper()
                signals.append(result)
        except Exception as e:
            logger.error(f"Detector failed for {symbol}: {e}")

    # Build human-readable summary
    if not signals:
        summary = f"No active signals for {symbol.upper()} right now — market appears neutral."
    else:
        bullish = [s for s in signals if s["direction"] == "bullish"]
        bearish = [s for s in signals if s["direction"] == "bearish"]
        parts = []
        if bullish:
            parts.append(f"{len(bullish)} bullish signal{'s' if len(bullish) > 1 else ''}")
        if bearish:
            parts.append(f"{len(bearish)} bearish signal{'s' if len(bearish) > 1 else ''}")
        summary = f"{symbol.upper()} has {' and '.join(parts)} active right now."

    return {
        "symbol": symbol.upper(),
        "has_data": True,
        "as_of": latest["date"].isoformat(),
        "current_price": round(float(latest["close"]), 2),
        "signal_count": len(signals),
        "bullish_count": len([s for s in signals if s["direction"] == "bullish"]),
        "bearish_count": len([s for s in signals if s["direction"] == "bearish"]),
        "signals": signals,
        "summary": summary,
        "disclaimer": (
            "⚠ These are pattern-based signals, not financial advice. "
            "Always do your own research before making any trade."
        ),
    }


def scan_watchlist(db: Session) -> list[dict]:
    """
    Scan all tracked tickers and return signals for each.
    Sorted by signal count descending — most active tickers first.
    """
    tickers = db.query(Ticker).order_by(Ticker.symbol).all()
    results = []

    for ticker in tickers:
        try:
            result = scan_ticker(db, ticker.symbol)
            results.append(result)
        except Exception as e:
            logger.error(f"Scan failed for {ticker.symbol}: {e}")
            results.append({
                "symbol": ticker.symbol,
                "has_data": False,
                "signals": [],
                "summary": f"Scan failed: {e}",
            })

    results.sort(key=lambda x: x.get("signal_count", 0), reverse=True)
    return results
