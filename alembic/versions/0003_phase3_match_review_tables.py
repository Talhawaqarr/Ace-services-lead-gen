"""Phase 3 match persistence and review workflow

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-20
"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'match_records',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('contractor_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('match_score', sa.Float(), nullable=False),
        sa.Column('raw_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('max_available_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('feature_completeness', sa.Float(), nullable=False, server_default='0'),
        sa.Column('confidence', sa.String(), nullable=False),
        sa.Column('matcher_version', sa.String(), nullable=False),
        sa.Column('ranking', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('positive_factors', sa.JSON(), nullable=True),
        sa.Column('negative_factors', sa.JSON(), nullable=True),
        sa.Column('unknown_factors', sa.JSON(), nullable=True),
        sa.Column('components', sa.JSON(), nullable=True),
        sa.Column('review_status', sa.String(), nullable=False, server_default='UNREVIEWED'),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    )
    op.create_foreign_key('fk_match_records_project_id', 'match_records', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('fk_match_records_contractor_id', 'match_records', 'contractors', ['contractor_id'], ['id'])
    op.create_index('ix_match_records_project_id', 'match_records', ['project_id'])
    op.create_index('ix_match_records_contractor_id', 'match_records', ['contractor_id'])
    op.create_index('ix_match_records_review_status', 'match_records', ['review_status'])
    op.create_unique_constraint('uq_match_records_project_contractor_version', 'match_records', ['project_id', 'contractor_id', 'matcher_version'])

    op.create_table(
        'match_review_audit',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('match_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('previous_status', sa.String(), nullable=False),
        sa.Column('new_status', sa.String(), nullable=False),
        sa.Column('actor', sa.String(), nullable=False, server_default='local-dev'),
        sa.Column('source', sa.String(), nullable=False, server_default='local-dev'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    )
    op.create_foreign_key('fk_match_review_audit_match_id', 'match_review_audit', 'match_records', ['match_id'], ['id'])
    op.create_index('ix_match_review_audit_match_id', 'match_review_audit', ['match_id'])


def downgrade():
    op.drop_constraint('uq_match_records_project_contractor_version', 'match_records', type_='unique')
    op.drop_index('ix_match_records_review_status', table_name='match_records')
    op.drop_index('ix_match_records_contractor_id', table_name='match_records')
    op.drop_index('ix_match_records_project_id', table_name='match_records')
    op.drop_constraint('fk_match_records_contractor_id', 'match_records', type_='foreignkey')
    op.drop_constraint('fk_match_records_project_id', 'match_records', type_='foreignkey')
    op.drop_table('match_review_audit')
    op.drop_table('match_records')
