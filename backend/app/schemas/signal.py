from datetime import datetime

from pydantic import BaseModel


class SignalResponse(BaseModel):
    id: int
    ticker_id: int
    symbol: str
    signal_type: str
    direction: str
    strength: float | None
    description: str | None
    is_past_opportunity: bool
    outcome_pct: float | None
    outcome_days: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OpportunitySummary(BaseModel):
    symbol: str
    date: str
    signal_type: str
    direction: str
    description: str
    outcome_pct: float | None  # What actually happened
    outcome_days: int | None
