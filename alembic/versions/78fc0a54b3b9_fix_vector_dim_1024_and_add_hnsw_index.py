"""fix vector dim 1024 and add hnsw index

Revision ID: 78fc0a54b3b9
Revises: a3905354d158
Create Date: 2026-03-19

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "78fc0a54b3b9"
down_revision: Union[str, Sequence[str], None] = "a3905354d158"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix vector column from 1536 to 1024 (BGE-M3) and add HNSW index."""
    # Step 1: Alter vector column dimension (all NULLs currently, safe change)
    op.execute("ALTER TABLE products ALTER COLUMN vector TYPE vector(1024)")

    # Step 2: Create HNSW index for cosine similarity search
    op.execute(
        "CREATE INDEX ix_products_vector_hnsw ON products "
        "USING hnsw (vector vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    """Revert HNSW index and restore vector column to 1536."""
    op.execute("DROP INDEX IF EXISTS ix_products_vector_hnsw")
    op.execute("ALTER TABLE products ALTER COLUMN vector TYPE vector(1536)")
