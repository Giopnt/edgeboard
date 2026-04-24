from datetime import date, datetime

from sqlalchemy import Date, Float, Integer, String, Text, ForeignKey, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class SentimentScore(Base):
    __tablename__ = "sentiment_scores"
    __table_args__ = (
        UniqueConstraint("ticker_id", "date", name="uq_sentiment_ticker_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticker_id: Mapped[int] = mapped_column(ForeignKey("tickers.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # VADER composite score: -1.0 (very negative) to +1.0 (very positive)
    compound_score: Mapped[float] = mapped_column(Float, nullable=False)
    positive: Mapped[float | None] = mapped_column(Float)
    neutral: Mapped[float | None] = mapped_column(Float)
    negative: Mapped[float | None] = mapped_column(Float)

    headline_count: Mapped[int] = mapped_column(Integer, default=0)

    # Human-readable label derived from compound_score
    label: Mapped[str | None] = mapped_column(String(20))  # bullish / bearish / neutral

    # Store raw headlines as JSON string for debugging
    headlines_json: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    ticker = relationship("Ticker", back_populates="sentiments")

    def __repr__(self) -> str:
        return f"<SentimentScore {self.ticker_id} {self.date} score={self.compound_score}>"
