"""Preserve original announcement identity and official speech timestamp.

Revision ID: 20261016_0005
Revises: 20261016_0004

0001 uses dynamic metadata.create_all, so on fresh schemas these columns
may already exist before this migration. Inspect rather than recreate.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261016_0005"
down_revision = "20261016_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = {col["name"] for col in sa.inspect(op.get_bind()).get_columns("public_documents")}
    if "source_published_at" not in existing:
        op.add_column("public_documents", sa.Column(
            "source_published_at", sa.DateTime(timezone=True), nullable=True,
        ))
    if "source_metadata" not in existing:
        op.add_column("public_documents", sa.Column(
            "source_metadata", sa.JSON().with_variant(JSONB(), "postgresql"),
            nullable=False, server_default=sa.text("'{}'"),
        ))


def downgrade() -> None:
    existing = {col["name"] for col in sa.inspect(op.get_bind()).get_columns("public_documents")}
    if "source_metadata" in existing:
        op.drop_column("public_documents", "source_metadata")
    if "source_published_at" in existing:
        op.drop_column("public_documents", "source_published_at")
