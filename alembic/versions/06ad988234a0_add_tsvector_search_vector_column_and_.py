"""add tsvector search_vector column and GIN index

Revision ID: 06ad988234a0
Revises: 78fc0a54b3b9
Create Date: 2026-03-20

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "06ad988234a0"
down_revision: Union[str, Sequence[str], None] = "78fc0a54b3b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tsvector column, populate from existing data, create GIN index, and trigger."""
    # Step 1: Add search_vector column of type tsvector
    op.execute("ALTER TABLE products ADD COLUMN search_vector tsvector")

    # Step 2: Populate search_vector from existing data
    op.execute(
        "UPDATE products SET search_vector = to_tsvector('french', "
        "coalesce(name, '') || ' ' || coalesce(reference, '') || ' ' || "
        "coalesce(category, '') || ' ' || coalesce(description, ''))"
    )

    # Step 3: Create GIN index for fast full-text search
    op.execute(
        "CREATE INDEX ix_products_search_vector_gin "
        "ON products USING gin(search_vector)"
    )

    # Step 4: Create trigger to keep search_vector in sync on INSERT/UPDATE
    op.execute(
        """
        CREATE OR REPLACE FUNCTION products_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('french',
                coalesce(NEW.name, '') || ' ' ||
                coalesce(NEW.reference, '') || ' ' ||
                coalesce(NEW.category, '') || ' ' ||
                coalesce(NEW.description, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_products_search_vector
        BEFORE INSERT OR UPDATE OF name, reference, category, description
        ON products
        FOR EACH ROW
        EXECUTE FUNCTION products_search_vector_update();
        """
    )


def downgrade() -> None:
    """Drop trigger, GIN index, and search_vector column."""
    op.execute("DROP TRIGGER IF EXISTS trg_products_search_vector ON products")
    op.execute("DROP FUNCTION IF EXISTS products_search_vector_update()")
    op.execute("DROP INDEX IF EXISTS ix_products_search_vector_gin")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS search_vector")
