"""Add archived public documents and passage offsets.

Revision ID: 20261016_0004
Revises: 20261016_0003

Migration 0001 imports dynamic Base.metadata. On fresh databases, it may
already create these tables: do not recreate and do not edit deployed 0001.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261016_0004"
down_revision = "20261016_0003"
branch_labels = None
depends_on = None

DOC = "public_documents"
CHUNKS = "public_document_chunks"
DOC_COLUMNS = {
    "id", "document_key", "version", "company_key", "title",
    "source_url", "source_type", "published_at", "retrieved_at",
    "valid_from", "valid_to", "content_sha256", "original_text",
    "verification_status",
}
CHUNK_COLUMNS = {
    "id", "document_record_id", "ordinal", "start_offset",
    "end_offset", "content_sha256", "content",
}


def _exists(table: str, required: set[str]) -> bool:
    insp = sa.inspect(op.get_bind())
    if not insp.has_table(table):
        return False
    columns = {item["name"] for item in insp.get_columns(table)}
    missing = required - columns
    if missing:
        raise RuntimeError(f"Incompatible {table}: missing {sorted(missing)}")
    return True


def _index(table: str, name: str, columns: list[str]) -> None:
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes(table)}
    if name not in indexes:
        op.create_index(name, table, columns)


def upgrade() -> None:
    if not _exists(DOC, DOC_COLUMNS):
        op.create_table(
            DOC,
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("document_key", sa.String(160), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("company_key", sa.String(160), nullable=False),
            sa.Column("title", sa.String(600), nullable=False),
            sa.Column("source_url", sa.Text(), nullable=False),
            sa.Column("source_type", sa.String(40), nullable=False),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
            sa.Column("valid_to", sa.DateTime(timezone=True)),
            sa.Column("content_sha256", sa.String(64), nullable=False),
            sa.Column("original_text", sa.Text(), nullable=False),
            sa.Column("verification_status", sa.String(20), nullable=False),
            sa.UniqueConstraint("document_key", "version", name="uq_public_document_version"),
            sa.CheckConstraint("version > 0", name="ck_public_document_version"),
            sa.CheckConstraint("length(content_sha256) = 64", name="ck_public_document_hash"),
            sa.CheckConstraint("verification_status = 'unverified'", name="ck_public_document_unverified"),
            sa.CheckConstraint("valid_to IS NULL OR valid_to > valid_from", name="ck_public_document_validity"),
        )
    _index(DOC, "ix_public_documents_key_time", ["document_key", "valid_from", "valid_to"])
    if not _exists(CHUNKS, CHUNK_COLUMNS):
        op.create_table(
            CHUNKS,
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("document_record_id", sa.String(36),
                      sa.ForeignKey("public_documents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("ordinal", sa.Integer(), nullable=False),
            sa.Column("start_offset", sa.Integer(), nullable=False),
            sa.Column("end_offset", sa.Integer(), nullable=False),
            sa.Column("content_sha256", sa.String(64), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.UniqueConstraint("document_record_id", "ordinal", name="uq_document_chunk_ordinal"),
            sa.CheckConstraint("start_offset >= 0 AND end_offset > start_offset", name="ck_document_chunk_offsets"),
            sa.CheckConstraint("length(content_sha256) = 64", name="ck_document_chunk_hash"),
        )
    _index(CHUNKS, "ix_document_chunks_document", ["document_record_id", "ordinal"])


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table(CHUNKS):
        op.drop_table(CHUNKS)
    if sa.inspect(op.get_bind()).has_table(DOC):
        op.drop_table(DOC)
