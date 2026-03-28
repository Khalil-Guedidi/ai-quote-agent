"""add knowledge_documents table

Revision ID: b1a2c3d4e5f6
Revises: 24ece7f6fefc
Create Date: 2026-03-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]

# revision identifiers, used by Alembic.
revision: str = "b1a2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "24ece7f6fefc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create knowledge_documents table with HNSW and GIN indexes."""
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("source", sa.String(), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vector", Vector(dim=1024), nullable=True),
        sa.Column("search_vector", sa.dialects.postgresql.TSVECTOR(), nullable=True),
        sa.Column("metadata_", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_knowledge_documents"),
    )

    # HNSW index for cosine similarity search (same params as products table)
    op.execute(
        "CREATE INDEX ix_knowledge_documents_vector_hnsw ON knowledge_documents "
        "USING hnsw (vector vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )

    # GIN index on search_vector for keyword fallback
    op.execute(
        "CREATE INDEX ix_knowledge_documents_search_vector ON knowledge_documents "
        "USING gin (search_vector)"
    )

    # Index on is_active for filtering
    op.create_index("ix_knowledge_documents_is_active", "knowledge_documents", ["is_active"])

    # Index on title + source for document management queries
    op.create_index("ix_knowledge_documents_title", "knowledge_documents", ["title"])


def downgrade() -> None:
    """Drop knowledge_documents table and all indexes."""
    op.drop_index("ix_knowledge_documents_title", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_is_active", table_name="knowledge_documents")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_documents_search_vector")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_documents_vector_hnsw")
    op.drop_table("knowledge_documents")
