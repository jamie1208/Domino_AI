"""Add successful source-ingestion receipts safely across dynamic 0001 metadata.

Revision ID: 20261016_0003
Revises: 20261016_0002

Migration 0001 historically runs Base.metadata.create_all, so a fresh schema
may already contain this table/index before reaching revision 0003. Do not
change a deployed migration; verify existing objects and create only missing
ones. Reject incompatible pre-existing tables rather than marking them valid.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261016_0003"
down_revision = "20261016_0002"
branch_labels = None
depends_on = None

TABLE = "source_ingestion_runs"
INDEX = "ix_source_runs_key_retrieved"
REQUIRED_COLUMNS = {
    "id", "source_key", "source_url", "dataset_url", "retrieved_at",
    "recorded_at", "payload_sha256", "accepted_rows", "rejected_rows",
    "created_versions", "unchanged_rows", "status",
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(TABLE):
        op.create_table(
            TABLE,
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("source_key", sa.String(80), nullable=False),
            sa.Column("source_url", sa.Text(), nullable=False),
            sa.Column("dataset_url", sa.Text(), nullable=False),
            sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("payload_sha256", sa.String(64), nullable=False),
            sa.Column("accepted_rows", sa.Integer(), nullable=False),
            sa.Column("rejected_rows", sa.Integer(), nullable=False),
            sa.Column("created_versions", sa.Integer(), nullable=False),
            sa.Column("unchanged_rows", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(16), nullable=False),
            sa.CheckConstraint("status = 'success'", name="ck_source_runs_status"),
            sa.CheckConstraint("length(payload_sha256) = 64", name="ck_source_runs_hash"),
            sa.CheckConstraint(
                "accepted_rows >= 0 AND rejected_rows >= 0 AND created_versions >= 0 AND unchanged_rows >= 0",
                name="ck_source_runs_counts",
            ),
        )
    else:
        # 0001's dynamic metadata may create the table on fresh databases.
        # Fail closed when an unrelated/incomplete table has the same name.
        actual = {column["name"] for column in inspector.get_columns(TABLE)}
        missing = REQUIRED_COLUMNS - actual
        if missing:
            raise RuntimeError(
                "Existing source_ingestion_runs has incompatible columns: "
                + ", ".join(sorted(missing))
            )

    indexes = {item["name"] for item in sa.inspect(bind).get_indexes(TABLE)}
    if INDEX not in indexes:
        op.create_index(INDEX, TABLE, ["source_key", "retrieved_at"])


def downgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table(TABLE):
        indexes = {item["name"] for item in sa.inspect(bind).get_indexes(TABLE)}
        if INDEX in indexes:
            op.drop_index(INDEX, table_name=TABLE)
        op.drop_table(TABLE)
