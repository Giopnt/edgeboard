from datetime import date, datetime

from pydantic import BaseModel


class SentimentResponse(BaseModel):
    id: int
    ticker_id: int
    date: date
    compound_score: float
    positive: float | None
    neutral: float | None
    negative: float | None
    headline_count: int
    label: str | None

    model_config = {"from_attributes": True}


class SentimentSummary(BaseModel):
    symbol: str
    avg_score_7d: float | None
    avg_score_30d: float | None
    latest_label: str | None
    latest_score: float | None
    latest_date: date | None
    trend: str | None  # "improving", "worsening", "stable"
