"""add outreach queue items

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "outreach_queue_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outreach_drafts.id"), nullable=False),
        sa.Column("recipient_email", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("body", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="QUEUED"),
        sa.Column("queued_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("provenance", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("draft_id", name="uq_outreach_queue_items_draft_id"),
    )
    op.create_index("ix_outreach_queue_items_status", "outreach_queue_items", ["status"])

def downgrade():
    op.drop_index("ix_outreach_queue_items_status", table_name="outreach_queue_items")
    op.drop_table("outreach_queue_items")
