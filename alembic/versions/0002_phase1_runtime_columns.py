"""Phase 1 runtime columns and dedupe constraints

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-20
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('projects', sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True))
    op.add_column('projects', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True))
    op.add_column('contractors', sa.Column('source', sa.String(), nullable=True))
    op.add_column('contractors', sa.Column('source_id', sa.String(), nullable=True))
    op.add_column('contractors', sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True))
    op.add_column('contractors', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True))
    op.execute("UPDATE contractors SET source = 'synthetic', source_id = id::text WHERE source IS NULL")
    op.alter_column('contractors', 'source', nullable=False)
    op.alter_column('contractors', 'source_id', nullable=False)
    op.create_unique_constraint('uq_contractors_source_source_id', 'contractors', ['source', 'source_id'])
    op.create_unique_constraint('uq_projects_source_source_id', 'projects', ['source', 'source_id'])


def downgrade():
    op.drop_constraint('uq_contractors_source_source_id', 'contractors', type_='unique')
    op.drop_constraint('uq_projects_source_source_id', 'projects', type_='unique')
    op.drop_column('contractors', 'updated_at')
    op.drop_column('contractors', 'created_at')
    op.drop_column('contractors', 'source_id')
    op.drop_column('contractors', 'source')
    op.drop_column('projects', 'updated_at')
    op.drop_column('projects', 'created_at')
