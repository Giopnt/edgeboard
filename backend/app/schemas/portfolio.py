from datetime import datetime

from pydantic import BaseModel


class PositionCreate(BaseModel):
    symbol: str
    shares: float
    avg_cost: float
    opened_at: datetime


class PositionResponse(BaseModel):
    id: int
    ticker_id: int
    symbol: str
    shares: float
    avg_cost: float
    cost_basis: float
    current_price: float | None = None
    current_value: float | None = None
    unrealized_pnl: float | None = None
    unrealized_pnl_pct: float | None = None

    model_config = {"from_attributes": True}


class RiskSnapshot(BaseModel):
    total_cost_basis: float
    total_current_value: float | None
    total_unrealized_pnl: float | None
    total_unrealized_pnl_pct: float | None

    # Concentration
    positions: list[PositionResponse]
    largest_position_pct: float | None  # % of portfolio in single biggest position
    top_3_concentration_pct: float | None

    # Drawdown scenarios
    drawdown_5pct: float   # How much $ you lose if portfolio drops 5%
    drawdown_10pct: float
    drawdown_20pct: float

    # Warnings
    warnings: list[str]  # e.g. "NVDA is 45% of your portfolio"
