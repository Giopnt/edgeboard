from datetime import datetime, date

from sqlalchemy import Float, String, Text, ForeignKey, DateTime, Boolean, Date, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticker_id: Mapped[int] = mapped_column(ForeignKey("tickers.id"), nullable=False, index=True)

    # Signal classification
    signal_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # e.g. "rsi_oversold", "volume_spike", "sentiment_spike", "price_breakout"

    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    # "bullish" or "bearish"

    strength: Mapped[float | None] = mapped_column(Float)
    # 0.0 to 1.0 — how strong is this signal

    is_past_opportunity: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    # True = historical opportunity, False = forward-looking signal

    # Human-readable description
    description: Mapped[str | None] = mapped_column(Text)

    # For past opportunities: what actually happened after
    outcome_pct: Mapped[float | None] = mapped_column(Float)
    outcome_days: Mapped[int | None] = mapped_column(Float)

    # Mark signals as dismissed/acted on
    signal_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    ticker = relationship("Ticker", back_populates="signals")

    def __repr__(self) -> str:
        return f"<Signal {self.ticker_id} {self.signal_type} {self.direction}>"