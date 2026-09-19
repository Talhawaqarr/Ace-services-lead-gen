"""Phase 5 ingestion tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-20
"""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'raw_projects',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('source_id', sa.String(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.Column('raw_payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='RECEIVED'),
        sa.Column('error_detail', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    )
    op.create_unique_constraint('uq_raw_projects_source_source_id', 'raw_projects', ['source', 'source_id'])
    op.create_index('ix_raw_projects_source', 'raw_projects', ['source'])
    op.create_index('ix_raw_projects_status', 'raw_projects', ['status'])

    op.create_table(
        'ingestion_runs',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='RUNNING'),
        sa.Column('records_fetched', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('accepted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rejected', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duplicates', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('errors', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    )
    op.create_index('ix_ingestion_runs_source', 'ingestion_runs', ['source'])
    op.create_index('ix_ingestion_runs_status', 'ingestion_runs', ['status'])


def downgrade():
    op.drop_index('ix_ingestion_runs_status', table_name='ingestion_runs')
    op.drop_index('ix_ingestion_runs_source', table_name='ingestion_runs')
    op.drop_table('ingestion_runs')
    op.drop_index('ix_raw_projects_status', table_name='raw_projects')
    op.drop_index('ix_raw_projects_source', table_name='raw_projects')
    op.drop_constraint('uq_raw_projects_source_source_id', 'raw_projects', type_='unique')
    op.drop_table('raw_projects')
