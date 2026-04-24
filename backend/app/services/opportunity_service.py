import logging
from datetime import date, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from app.models.ticker import Ticker
from app.models.price import PriceHistory
from app.models.signal import Signal

logger = logging.getLogger(__name__)

# ── Technical indicators ──────────────────────────────────────────────────────

def compute_rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    """Compute RSI (Relative Strength Index)."""
    delta = closes.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, float("nan"))  # NaN when no losses
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(100)  # No losses = RSI 100 (fully overbought)


def compute_sma(closes: pd.Series, period: int) -> pd.Series:
    """Simple moving average."""
    return closes.rolling(window=period).mean()


def compute_volume_zscore(volumes: pd.Series, period: int = 20) -> pd.Series:
    """How many standard deviations is today's volume from the rolling mean."""
    mean = volumes.rolling(window=period).mean()
    std = volumes.rolling(window=period).std()
    return (volumes - mean) / std.replace(0, float("nan"))


# ── Pattern detectors ─────────────────────────────────────────────────────────

def detect_rsi_oversold(df: pd.DataFrame, threshold: float = 30.0) -> list[dict]:
    """
    Detect days where RSI dropped below threshold (oversold = potential bounce).
    Historically bullish signal.
    """
    opportunities = []
    if "rsi" not in df.columns or df["rsi"].isna().all():
        return opportunities

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]
        if pd.isna(row["rsi"]) or pd.isna(prev["rsi"]):
            continue
        if row["rsi"] < threshold and prev["rsi"] >= threshold:
            # Crossed into oversold — compute what happened next
            outcome = _compute_outcome(df, i)
            opportunities.append({
                "date": row["date"],
                "signal_type": "rsi_oversold",
                "direction": "bullish",
                "strength": round((threshold - row["rsi"]) / threshold, 4),
                "description": (
                    f"RSI crossed below {threshold:.0f} (was {prev['rsi']:.1f}, "
                    f"dropped to {row['rsi']:.1f}) — historically oversold, potential bounce"
                ),
                **outcome,
            })
    return opportunities


def detect_rsi_overbought(df: pd.DataFrame, threshold: float = 70.0) -> list[dict]:
    """
    Detect days where RSI crossed above threshold (overbought = potential pullback).
    Historically bearish signal.
    """
    opportunities = []
    if "rsi" not in df.columns or df["rsi"].isna().all():
        return opportunities

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]
        if pd.isna(row["rsi"]) or pd.isna(prev["rsi"]):
            continue
        if row["rsi"] > threshold and prev["rsi"] <= threshold:
            outcome = _compute_outcome(df, i)
            opportunities.append({
                "date": row["date"],
                "signal_type": "rsi_overbought",
                "direction": "bearish",
                "strength": round((row["rsi"] - threshold) / (100 - threshold), 4),
                "description": (
                    f"RSI crossed above {threshold:.0f} (was {prev['rsi']:.1f}, "
                    f"rose to {row['rsi']:.1f}) — historically overbought, potential pullback"
                ),
                **outcome,
            })
    return opportunities


def detect_volume_spikes(df: pd.DataFrame, zscore_threshold: float = 2.0) -> list[dict]:
    """
    Detect days with unusually high volume (2+ standard deviations above mean).
    Volume spikes often precede significant price moves.
    """
    opportunities = []
    if "volume_zscore" not in df.columns:
        return opportunities

    for i in range(len(df)):
        row = df.iloc[i]
        if pd.isna(row.get("volume_zscore")) or row["volume_zscore"] < zscore_threshold:
            continue

        direction = "bullish" if row["pct_change"] >= 0 else "bearish"
        outcome = _compute_outcome(df, i)
        opportunities.append({
            "date": row["date"],
            "signal_type": "volume_spike",
            "direction": direction,
            "strength": round(min(row["volume_zscore"] / 5.0, 1.0), 4),
            "description": (
                f"Volume {row['volume_zscore']:.1f}x above normal on a "
                f"{'up' if direction == 'bullish' else 'down'} day "
                f"({row['pct_change']:+.2f}%) — unusual activity"
            ),
            **outcome,
        })
    return opportunities


def detect_golden_cross(df: pd.DataFrame) -> list[dict]:
    """
    Detect golden cross: 20-day SMA crosses above 50-day SMA.
    Classic bullish signal.
    """
    opportunities = []
    if "sma20" not in df.columns or "sma50" not in df.columns:
        return opportunities

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]
        if any(pd.isna(v) for v in [row["sma20"], row["sma50"], prev["sma20"], prev["sma50"]]):
            continue
        if prev["sma20"] <= prev["sma50"] and row["sma20"] > row["sma50"]:
            outcome = _compute_outcome(df, i)
            opportunities.append({
                "date": row["date"],
                "signal_type": "golden_cross",
                "direction": "bullish",
                "strength": round(min((row["sma20"] - row["sma50"]) / row["sma50"], 1.0), 4),
                "description": (
                    f"20-day SMA (${row['sma20']:.2f}) crossed above "
                    f"50-day SMA (${row['sma50']:.2f}) — classic bullish momentum signal"
                ),
                **outcome,
            })
    return opportunities


def detect_death_cross(df: pd.DataFrame) -> list[dict]:
    """
    Detect death cross: 20-day SMA crosses below 50-day SMA.
    Classic bearish signal.
    """
    opportunities = []
    if "sma20" not in df.columns or "sma50" not in df.columns:
        return opportunities

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]
        if any(pd.isna(v) for v in [row["sma20"], row["sma50"], prev["sma20"], prev["sma50"]]):
            continue
        if prev["sma20"] >= prev["sma50"] and row["sma20"] < row["sma50"]:
            outcome = _compute_outcome(df, i)
            opportunities.append({
                "date": row["date"],
                "signal_type": "death_cross",
                "direction": "bearish",
                "strength": round(min((row["sma50"] - row["sma20"]) / row["sma50"], 1.0), 4),
                "description": (
                    f"20-day SMA (${row['sma20']:.2f}) crossed below "
                    f"50-day SMA (${row['sma50']:.2f}) — classic bearish momentum signal"
                ),
                **outcome,
            })
    return opportunities


def detect_big_moves(df: pd.DataFrame, threshold: float = 4.0) -> list[dict]:
    """
    Detect days with large single-day price moves (>4%).
    These are the days traders most want to know about in hindsight.
    """
    opportunities = []
    for i in range(len(df)):
        row = df.iloc[i]
        if pd.isna(row.get("pct_change")):
            continue
        if abs(row["pct_change"]) >= threshold:
            direction = "bullish" if row["pct_change"] > 0 else "bearish"
            outcome = _compute_outcome(df, i)
            opportunities.append({
                "date": row["date"],
                "signal_type": "big_move",
                "direction": direction,
                "strength": round(min(abs(row["pct_change"]) / 10.0, 1.0), 4),
                "description": (
                    f"Stock moved {row['pct_change']:+.2f}% in a single day "
                    f"(close: ${row['close']:.2f}) — significant price action"
                ),
                **outcome,
            })
    return opportunities


# ── Outcome calculator ────────────────────────────────────────────────────────

def _compute_outcome(df: pd.DataFrame, signal_idx: int, forward_days: int = 5) -> dict:
    """
    Given a signal at index i, compute what the price did over the next N days.
    Returns outcome_pct and outcome_days.
    """
    if signal_idx >= len(df) - 1:
        return {"outcome_pct": None, "outcome_days": None}

    signal_close = df.iloc[signal_idx]["close"]
    end_idx = min(signal_idx + forward_days, len(df) - 1)
    end_close = df.iloc[end_idx]["close"]

    if signal_close and signal_close > 0:
        outcome_pct = round(((end_close - signal_close) / signal_close) * 100, 2)
        actual_days = end_idx - signal_idx
        return {"outcome_pct": outcome_pct, "outcome_days": actual_days}

    return {"outcome_pct": None, "outcome_days": None}


# ── Main engine ───────────────────────────────────────────────────────────────

def build_price_dataframe(db: Session, ticker_id: int, days: int = 365) -> pd.DataFrame:
    """Load price history from DB into a DataFrame with all indicators computed."""
    since = date.today() - timedelta(days=days)
    prices = (
        db.query(PriceHistory)
        .filter(PriceHistory.ticker_id == ticker_id, PriceHistory.date >= since)
        .order_by(PriceHistory.date.asc())
        .all()
    )

    if not prices:
        return pd.DataFrame()

    df = pd.DataFrame([{
        "date": p.date,
        "open": p.open,
        "high": p.high,
        "low": p.low,
        "close": p.close,
        "volume": p.volume,
        "pct_change": p.pct_change,
    } for p in prices])

    # Compute indicators
    df["rsi"] = compute_rsi(df["close"])
    df["sma20"] = compute_sma(df["close"], 20)
    df["sma50"] = compute_sma(df["close"], 50)
    df["volume_zscore"] = compute_volume_zscore(df["volume"].fillna(0).astype(float))

    return df


def run_opportunity_scan(
    db: Session,
    symbol: str,
    days: int = 365,
    store: bool = True,
) -> list[dict]:
    """
    Run all pattern detectors on a ticker's price history.
    Optionally store results as Signal records in DB.
    Returns list of opportunity dicts.
    """
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol.upper()).first()
    if not ticker:
        raise ValueError(f"Ticker {symbol} not found")

    df = build_price_dataframe(db, ticker.id, days=days)
    if df.empty:
        logger.warning(f"No price data for {symbol} — fetch prices first")
        return []

    # Run all detectors
    all_opportunities = []
    all_opportunities.extend(detect_rsi_oversold(df))
    all_opportunities.extend(detect_rsi_overbought(df))
    all_opportunities.extend(detect_volume_spikes(df))
    all_opportunities.extend(detect_golden_cross(df))
    all_opportunities.extend(detect_death_cross(df))
    all_opportunities.extend(detect_big_moves(df))

    # Sort by date descending
    all_opportunities.sort(key=lambda x: x["date"], reverse=True)

    if store:
        _store_opportunities(db, ticker, all_opportunities)

    # Add symbol to each
    for opp in all_opportunities:
        opp["symbol"] = symbol.upper()
        opp["date"] = opp["date"].isoformat()

    logger.info(f"Found {len(all_opportunities)} past opportunities for {symbol}")
    return all_opportunities


def _store_opportunities(db: Session, ticker: Ticker, opportunities: list[dict]) -> None:
    """Store opportunity signals in DB, skipping duplicates."""
    existing = {
        (s.created_at.date().isoformat(), s.signal_type)
        for s in db.query(Signal)
        .filter(Signal.ticker_id == ticker.id, Signal.is_past_opportunity == True)  # noqa
        .all()
    }

    for opp in opportunities:
        key = (opp["date"] if isinstance(opp["date"], str) else opp["date"].isoformat(), opp["signal_type"])
        if key in existing:
            continue

        strength = opp.get("strength")
        outcome_pct = opp.get("outcome_pct")
        outcome_days = opp.get("outcome_days")

        raw_date = opp.get("date")
        if isinstance(raw_date, str):
            from datetime import date as _date
            signal_date = _date.fromisoformat(raw_date)
        else:
            signal_date = raw_date

        signal = Signal(
            ticker_id=ticker.id,
            signal_type=opp["signal_type"],
            direction=opp["direction"],
            strength=float(strength) if strength is not None else None,
            description=opp.get("description"),
            is_past_opportunity=True,
            outcome_pct=float(outcome_pct) if outcome_pct is not None else None,
            outcome_days=float(outcome_days) if outcome_days is not None else None,
            signal_date=signal_date,
            is_active=True,
        )
        db.add(signal)

    db.commit()
    logger.info(f"Stored opportunities for {ticker.symbol}")


def get_best_missed_opportunities(
    db: Session,
    symbol: str,
    days: int = 30,
    limit: int = 5,
) -> list[dict]:
    """
    Return the top N past opportunities ranked by absolute outcome_pct.
    These are the 'you could have made/saved X%' moments.
    """
    opportunities = run_opportunity_scan(db, symbol, days=days, store=False)
    scored = [o for o in opportunities if o.get("outcome_pct") is not None]
    scored.sort(key=lambda x: abs(x["outcome_pct"]), reverse=True)
    return scored[:limit]