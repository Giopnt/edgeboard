# Import all models here so Alembic can auto-detect them for migrations
from app.models.ticker import Ticker
from app.models.price import PriceHistory
from app.models.sentiment import SentimentScore
from app.models.position import Position
from app.models.signal import Signal

__all__ = ["Ticker", "PriceHistory", "SentimentScore", "Position", "Signal"]
