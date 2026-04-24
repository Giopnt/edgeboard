"""add signal_date to signals

Revision ID: 0002_add_signal_date
Revises: 0001_create_core_tables
Create Date: 2025-01-02 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002_add_signal_date"
down_revision: Union[str, None] = "0001_create_core_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("signals", sa.Column("signal_date", sa.Date(), nullable=True, index=True))


def downgrade() -> None:
    op.drop_column("signals", "signal_date")
