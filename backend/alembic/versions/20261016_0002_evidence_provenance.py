"""Persist evidence independence provenance.

Revision ID: 20261016_0002
Revises: 20261016_0001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '20261016_0002'
down_revision = '20261016_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {item['name'] for item in inspector.get_columns('evidence')}
    additions = {
        'independently_verified': sa.Column('independently_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
        'normalized_source_host': sa.Column('normalized_source_host', sa.String(length=253), nullable=True),
        'publisher_key': sa.Column('publisher_key', sa.String(length=240), nullable=True),
        'original_source_key': sa.Column('original_source_key', sa.String(length=240), nullable=True),
        'independence_basis': sa.Column('independence_basis', sa.String(length=60), nullable=True),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column('evidence', column)
    unique_constraints = {item['name'] for item in inspector.get_unique_constraints('evidence')}
    if 'uq_evidence_stable_id_hash' in unique_constraints:
        op.drop_constraint('uq_evidence_stable_id_hash', 'evidence', type_='unique')
    checks = {item['name'] for item in inspect(bind).get_check_constraints('evidence')}
    if 'ck_evidence_independence_basis' not in checks:
        op.create_check_constraint('ck_evidence_independence_basis', 'evidence', "independence_basis IS NULL OR independence_basis IN ('publisher_and_original_source','manual_review')")
    op.alter_column('evidence', 'independently_verified', server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    checks = {item['name'] for item in inspect(bind).get_check_constraints('evidence')}
    if 'ck_evidence_independence_basis' in checks:
        op.drop_constraint('ck_evidence_independence_basis', 'evidence', type_='check')
    op.create_unique_constraint('uq_evidence_stable_id_hash', 'evidence', ['evidence_id', 'content_hash'])
    for name in ('independence_basis', 'original_source_key', 'publisher_key', 'normalized_source_host', 'independently_verified'):
        op.drop_column('evidence', name)
