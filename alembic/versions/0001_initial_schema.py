"""initial schema

Revision ID: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'projects',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('source_id', sa.String(), nullable=False),
        sa.Column('city', sa.String()),
        sa.Column('state', sa.String(length=2)),
        sa.Column('latitude', sa.Float()),
        sa.Column('longitude', sa.Float()),
        sa.Column('trades', sa.JSON()),
        sa.Column('bid_date', sa.String()),
        sa.Column('estimated_value', sa.Float()),
        sa.Column('provenance', sa.JSON()),
    )
    op.create_table(
        'contractors',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_name', sa.String(), nullable=False),
        sa.Column('normalized_name', sa.String()),
        sa.Column('city', sa.String()),
        sa.Column('state', sa.String(length=2)),
        sa.Column('trades', sa.JSON()),
        sa.Column('primary_email', sa.String()),
        sa.Column('provenance', sa.JSON()),
    )


def downgrade():
    op.drop_table('contractors')
    op.drop_table('projects')
