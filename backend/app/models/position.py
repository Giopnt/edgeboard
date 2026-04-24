from datetime import datetime

from sqlalchemy import Float, ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticker_id: Mapped[int] = mapped_column(ForeignKey("tickers.id"), nullable=False, index=True)

    shares: Mapped[float] = mapped_column(Float, nullable=False)
    avg_cost: Mapped[float] = mapped_column(Float, nullable=False)  # Average cost per share

    is_open: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    ticker = relationship("Ticker", back_populates="positions")

    @property
    def cost_basis(self) -> float:
        return self.shares * self.avg_cost

    def __repr__(self) -> str:
        return f"<Position {self.ticker_id} shares={self.shares} avg_cost={self.avg_cost}>"
