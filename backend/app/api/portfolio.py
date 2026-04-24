from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.ticker import Ticker
from app.models.position import Position
from app.schemas.portfolio import PositionCreate, RiskSnapshot
from app.services.risk_service import build_risk_snapshot, enrich_position, get_current_price

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/risk")
def get_risk_snapshot(db: Session = Depends(get_db)):
    """
    Full portfolio risk snapshot.
    Returns live P&L, concentration metrics, drawdown scenarios, and warnings.
    """
    return build_risk_snapshot(db)


@router.get("/positions")
def list_positions(db: Session = Depends(get_db)):
    """List all open positions with live prices and P&L."""
    positions = (
        db.query(Position, Ticker)
        .join(Ticker, Position.ticker_id == Ticker.id)
        .filter(Position.is_open == True)  # noqa: E712
        .order_by(Ticker.symbol)
        .all()
    )

    enriched = []
    for position, ticker in positions:
        price = get_current_price(ticker.symbol)
        enriched.append(enrich_position(position, ticker.symbol, price))

    return {"positions": enriched, "total": len(enriched)}


@router.post("/positions", status_code=status.HTTP_201_CREATED)
def create_position(payload: PositionCreate, db: Session = Depends(get_db)):
    """
    Add a new position to your portfolio.
    The ticker must already exist in your watchlist.
    """
    ticker = db.query(Ticker).filter(Ticker.symbol == payload.symbol.upper()).first()
    if not ticker:
        raise HTTPException(
            status_code=404,
            detail=f"{payload.symbol.upper()} not found. Add it to your watchlist first via POST /api/tickers",
        )

    position = Position(
        ticker_id=ticker.id,
        shares=payload.shares,
        avg_cost=payload.avg_cost,
        opened_at=payload.opened_at,
        is_open=True,
    )
    db.add(position)
    db.commit()
    db.refresh(position)

    current_price = get_current_price(ticker.symbol)
    return enrich_position(position, ticker.symbol, current_price)


@router.delete("/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
def close_position(position_id: int, db: Session = Depends(get_db)):
    """Mark a position as closed."""
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    position.is_open = False
    position.closed_at = datetime.now(timezone.utc)
    db.commit()


@router.get("/summary")
def get_portfolio_summary(db: Session = Depends(get_db)):
    """
    Quick portfolio summary — total value, total P&L, number of positions.
    Lighter than /risk — no concentration or drawdown calculations.
    """
    snapshot = build_risk_snapshot(db)
    return {
        "total_positions": len(snapshot["positions"]),
        "total_cost_basis": snapshot["total_cost_basis"],
        "total_current_value": snapshot["total_current_value"],
        "total_unrealized_pnl": snapshot["total_unrealized_pnl"],
        "total_unrealized_pnl_pct": snapshot["total_unrealized_pnl_pct"],
        "warnings_count": len(snapshot["warnings"]),
    }