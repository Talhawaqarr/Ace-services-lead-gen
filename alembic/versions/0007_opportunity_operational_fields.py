"""add canonical opportunity operational fields

Revision ID: 0007
"""
from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("projects", sa.Column("posted_date", sa.String(), nullable=True))
    op.add_column("projects", sa.Column("response_deadline", sa.String(), nullable=True))
    op.add_column("projects", sa.Column("status", sa.String(), nullable=True))
    op.add_column("projects", sa.Column("description", sa.String(), nullable=True))
    op.add_column("projects", sa.Column("source_url", sa.String(), nullable=True))


def downgrade():
    op.drop_column("projects", "source_url")
    op.drop_column("projects", "description")
    op.drop_column("projects", "status")
    op.drop_column("projects", "response_deadline")
    op.drop_column("projects", "posted_date")
