"""add contractor contact fields

Revision ID: 0011
Revises: 0010
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("contractors", sa.Column("primary_phone", sa.String(), nullable=True))
    op.add_column("contractors", sa.Column("website", sa.String(), nullable=True))

def downgrade():
    op.drop_column("contractors", "website")
    op.drop_column("contractors", "primary_phone")
