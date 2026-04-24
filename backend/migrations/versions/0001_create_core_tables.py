"""create core tables

Revision ID: 0001_create_core_tables
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001_create_core_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- tickers ---
    op.create_table(
        "tickers",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("symbol", sa.String(10), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("sector", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- price_history ---
    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("ticker_id", sa.Integer(), sa.ForeignKey("tickers.id"), nullable=False, index=True),
        sa.Column("date", sa.Date(), nullable=False, index=True),
        sa.Column("open", sa.Float(), nullable=True),
        sa.Column("high", sa.Float(), nullable=True),
        sa.Column("low", sa.Float(), nullable=True),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("pct_change", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("ticker_id", "date", name="uq_price_ticker_date"),
    )

    # --- sentiment_scores ---
    op.create_table(
        "sentiment_scores",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("ticker_id", sa.Integer(), sa.ForeignKey("tickers.id"), nullable=False, index=True),
        sa.Column("date", sa.Date(), nullable=False, index=True),
        sa.Column("compound_score", sa.Float(), nullable=False),
        sa.Column("positive", sa.Float(), nullable=True),
        sa.Column("neutral", sa.Float(), nullable=True),
        sa.Column("negative", sa.Float(), nullable=True),
        sa.Column("headline_count", sa.Integer(), default=0),
        sa.Column("label", sa.String(20), nullable=True),
        sa.Column("headlines_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("ticker_id", "date", name="uq_sentiment_ticker_date"),
    )

    # --- positions ---
    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("ticker_id", sa.Integer(), sa.ForeignKey("tickers.id"), nullable=False, index=True),
        sa.Column("shares", sa.Float(), nullable=False),
        sa.Column("avg_cost", sa.Float(), nullable=False),
        sa.Column("is_open", sa.Boolean(), default=True, index=True),
        sa.Column("opened_at", sa.DateTime(), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- signals ---
    op.create_table(
        "signals",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("ticker_id", sa.Integer(), sa.ForeignKey("tickers.id"), nullable=False, index=True),
        sa.Column("signal_type", sa.String(50), nullable=False, index=True),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("strength", sa.Float(), nullable=True),
        sa.Column("is_past_opportunity", sa.Boolean(), default=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("outcome_pct", sa.Float(), nullable=True),
        sa.Column("outcome_days", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, index=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), index=True),
    )


def downgrade() -> None:
    op.drop_table("signals")
    op.drop_table("positions")
    op.drop_table("sentiment_scores")
    op.drop_table("price_history")
    op.drop_table("tickers")
