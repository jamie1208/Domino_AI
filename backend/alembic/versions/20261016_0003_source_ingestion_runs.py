"""Keep a source ingestion receipt even when company profiles are unchanged.

Revision ID: 20261016_0003
Revises: 20261016_0002
"""
from alembic import op
import sqlalchemy as sa

revision = "20261016_0003"
down_revision = "20261016_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_ingestion_runs",
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
    op.create_index(
        "ix_source_runs_key_retrieved",
        "source_ingestion_runs",
        ["source_key", "retrieved_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_source_runs_key_retrieved", table_name="source_ingestion_runs")
    op.drop_table("source_ingestion_runs")
