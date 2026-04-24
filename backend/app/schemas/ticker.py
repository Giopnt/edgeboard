from datetime import datetime

from pydantic import BaseModel, field_validator


class TickerCreate(BaseModel):
    symbol: str
    name: str | None = None
    sector: str | None = None

    @field_validator("symbol")
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        return v.upper().strip()


class TickerResponse(BaseModel):
    id: int
    symbol: str
    name: str | None
    sector: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TickerList(BaseModel):
    tickers: list[TickerResponse]
    total: int
