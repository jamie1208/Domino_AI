"""Phase 4 PostgreSQL persistence foundation.

Revision ID: 20261016_0001
Revises: None
"""
from alembic import op

from app.db_models import Base

revision = '20261016_0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Metadata is pinned by this revision's application version. checkfirst makes
    # an interrupted initial setup recoverable; Alembic still records one revision.
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    for table in reversed(Base.metadata.sorted_tables):
        table.drop(bind=op.get_bind(), checkfirst=True)
