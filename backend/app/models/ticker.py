from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Ticker(Base):
    __tablename__ = "tickers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(200))
    sector: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    prices = relationship("PriceHistory", back_populates="ticker", cascade="all, delete-orphan")
    sentiments = relationship("SentimentScore", back_populates="ticker", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="ticker", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="ticker", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Ticker {self.symbol}>"
