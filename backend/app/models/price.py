from datetime import date, datetime

from sqlalchemy import Date, Float, BigInteger, ForeignKey, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (
        UniqueConstraint("ticker_id", "date", name="uq_price_ticker_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticker_id: Mapped[int] = mapped_column(ForeignKey("tickers.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    open: Mapped[float | None] = mapped_column(Float)
    high: Mapped[float | None] = mapped_column(Float)
    low: Mapped[float | None] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int | None] = mapped_column(BigInteger)

    # Computed daily change (stored for fast queries)
    pct_change: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    ticker = relationship("Ticker", back_populates="prices")

    def __repr__(self) -> str:
        return f"<PriceHistory {self.ticker_id} {self.date} close={self.close}>"
