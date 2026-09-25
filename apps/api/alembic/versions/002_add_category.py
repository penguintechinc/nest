"""Add category column to data_resources.

Revision ID: 002
Revises: 001
Create Date: 2026-09-22 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the derived category column (database|object|volume|streaming|search|analytics)."""
    op.add_column(
        "data_resources",
        sa.Column("category", sa.String(50), server_default=""),
    )


def downgrade() -> None:
    """Drop the category column."""
    op.drop_column("data_resources", "category")
