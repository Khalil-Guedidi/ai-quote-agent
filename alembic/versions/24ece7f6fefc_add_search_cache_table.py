"""Add search_cache table.

Revision ID: 24ece7f6fefc
Revises: 06ad988234a0
Create Date: 2026-03-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "24ece7f6fefc"
down_revision: str | None = "06ad988234a0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "search_cache",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("cache_key", sa.String(64), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("search_params", JSONB(), nullable=False),
        sa.Column("results_json", JSONB(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_search_cache"),
    )
    op.create_index("ix_search_cache_cache_key", "search_cache", ["cache_key"], unique=True)
    op.create_index("ix_search_cache_expires_at", "search_cache", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_search_cache_expires_at", table_name="search_cache")
    op.drop_index("ix_search_cache_cache_key", table_name="search_cache")
    op.drop_table("search_cache")
