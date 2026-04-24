import logging
from datetime import date

import yfinance as yf
from sqlalchemy.orm import Session

from app.models.ticker import Ticker
from app.models.position import Position
from app.models.price import PriceHistory

logger = logging.getLogger(__name__)


# ── Price helpers ─────────────────────────────────────────────────────────────

def get_current_price(symbol: str) -> float | None:
    """Fetch latest closing price from yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d")
        if hist.empty:
            return None
        return round(float(hist["Close"].iloc[-1]), 4)
    except Exception as e:
        logger.error(f"Failed to fetch price for {symbol}: {e}")
        return None


def get_current_prices(symbols: list[str]) -> dict[str, float | None]:
    """Fetch current prices for multiple symbols in one yfinance call."""
    if not symbols:
        return {}
    try:
        data = yf.download(symbols, period="2d", auto_adjust=True, progress=False)
        prices = {}
        if len(symbols) == 1:
            symbol = symbols[0]
            close = data["Close"]
            prices[symbol] = round(float(close.iloc[-1]), 4) if not close.empty else None
        else:
            for symbol in symbols:
                try:
                    close = data["Close"][symbol].dropna()
                    prices[symbol] = round(float(close.iloc[-1]), 4) if not close.empty else None
                except Exception:
                    prices[symbol] = None
        return prices
    except Exception as e:
        logger.error(f"Batch price fetch failed: {e}")
        return {s: None for s in symbols}


# ── Position enrichment ───────────────────────────────────────────────────────

def enrich_position(position: Position, symbol: str, current_price: float | None) -> dict:
    """Add current price, value, and P&L to a position."""
    cost_basis = round(position.shares * position.avg_cost, 2)
    current_value = round(position.shares * current_price, 2) if current_price else None
    unrealized_pnl = round(current_value - cost_basis, 2) if current_value is not None else None
    unrealized_pnl_pct = (
        round((unrealized_pnl / cost_basis) * 100, 2)
        if unrealized_pnl is not None and cost_basis > 0
        else None
    )

    return {
        "id": position.id,
        "ticker_id": position.ticker_id,
        "symbol": symbol,
        "shares": position.shares,
        "avg_cost": position.avg_cost,
        "cost_basis": cost_basis,
        "current_price": current_price,
        "current_value": current_value,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_pct": unrealized_pnl_pct,
    }


# ── Risk calculations ─────────────────────────────────────────────────────────

def compute_concentration(enriched_positions: list[dict], total_value: float) -> dict:
    """
    Compute concentration metrics.
    Returns largest single position % and top-3 concentration %.
    """
    if not enriched_positions or total_value == 0:
        return {"largest_position_pct": None, "top_3_concentration_pct": None}

    pcts = sorted(
        [
            (p["symbol"], round((p["current_value"] / total_value) * 100, 2))
            for p in enriched_positions
            if p["current_value"] is not None
        ],
        key=lambda x: x[1],
        reverse=True,
    )

    largest = pcts[0][1] if pcts else None
    top3 = round(sum(p[1] for p in pcts[:3]), 2) if pcts else None

    return {"largest_position_pct": largest, "top_3_concentration_pct": top3}


def compute_drawdown_scenarios(total_value: float | None) -> dict:
    """How much $ is lost at various drawdown levels."""
    if total_value is None:
        return {"drawdown_5pct": 0, "drawdown_10pct": 0, "drawdown_20pct": 0}
    return {
        "drawdown_5pct": round(total_value * 0.05, 2),
        "drawdown_10pct": round(total_value * 0.10, 2),
        "drawdown_20pct": round(total_value * 0.20, 2),
    }


def generate_warnings(enriched_positions: list[dict], total_value: float | None) -> list[str]:
    """Generate human-readable risk warnings."""
    warnings = []

    if not total_value or total_value == 0:
        return warnings

    for p in enriched_positions:
        if p["current_value"] is None:
            warnings.append(f"⚠ Could not fetch current price for {p['symbol']}")
            continue

        pct = (p["current_value"] / total_value) * 100

        if pct >= 40:
            warnings.append(
                f"🔴 {p['symbol']} makes up {pct:.1f}% of your portfolio — extremely concentrated"
            )
        elif pct >= 25:
            warnings.append(
                f"🟡 {p['symbol']} makes up {pct:.1f}% of your portfolio — consider trimming"
            )

        if p["unrealized_pnl_pct"] is not None and p["unrealized_pnl_pct"] <= -15:
            warnings.append(
                f"🔴 {p['symbol']} is down {abs(p['unrealized_pnl_pct']):.1f}% from your cost basis"
            )

    return warnings


# ── Main risk snapshot ────────────────────────────────────────────────────────

def build_risk_snapshot(db: Session) -> dict:
    """
    Build the full portfolio risk snapshot.
    Fetches all open positions, enriches with live prices, computes all metrics.
    """
    # Load all open positions with their ticker
    positions = (
        db.query(Position, Ticker)
        .join(Ticker, Position.ticker_id == Ticker.id)
        .filter(Position.is_open == True)  # noqa: E712
        .all()
    )

    if not positions:
        return {
            "total_cost_basis": 0,
            "total_current_value": None,
            "total_unrealized_pnl": None,
            "total_unrealized_pnl_pct": None,
            "positions": [],
            "largest_position_pct": None,
            "top_3_concentration_pct": None,
            "drawdown_5pct": 0,
            "drawdown_10pct": 0,
            "drawdown_20pct": 0,
            "warnings": ["No open positions found. Add positions to see your risk snapshot."],
        }

    # Fetch all current prices in one batch call
    symbols = [ticker.symbol for _, ticker in positions]
    current_prices = get_current_prices(symbols)

    # Enrich each position
    enriched = [
        enrich_position(position, ticker.symbol, current_prices.get(ticker.symbol))
        for position, ticker in positions
    ]

    # Totals
    total_cost_basis = round(sum(p["cost_basis"] for p in enriched), 2)
    values_available = [p["current_value"] for p in enriched if p["current_value"] is not None]
    total_current_value = round(sum(values_available), 2) if values_available else None
    total_unrealized_pnl = (
        round(total_current_value - total_cost_basis, 2)
        if total_current_value is not None
        else None
    )
    total_unrealized_pnl_pct = (
        round((total_unrealized_pnl / total_cost_basis) * 100, 2)
        if total_unrealized_pnl is not None and total_cost_basis > 0
        else None
    )

    concentration = compute_concentration(enriched, total_current_value or 0)
    drawdowns = compute_drawdown_scenarios(total_current_value)
    warnings = generate_warnings(enriched, total_current_value)

    return {
        "total_cost_basis": total_cost_basis,
        "total_current_value": total_current_value,
        "total_unrealized_pnl": total_unrealized_pnl,
        "total_unrealized_pnl_pct": total_unrealized_pnl_pct,
        "positions": enriched,
        **concentration,
        **drawdowns,
        "warnings": warnings,
    }