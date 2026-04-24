from datetime import date, datetime

from pydantic import BaseModel


class PriceResponse(BaseModel):
    id: int
    ticker_id: int
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float
    volume: int | None
    pct_change: float | None

    model_config = {"from_attributes": True}


class PriceFetchResponse(BaseModel):
    symbol: str
    records_added: int
    date_from: date | None
    date_to: date | None
    message: str
