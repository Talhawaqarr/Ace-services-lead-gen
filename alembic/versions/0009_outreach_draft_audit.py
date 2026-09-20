"""add outreach draft audit

Revision ID: 0009
Revises: 0008
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "outreach_draft_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outreach_drafts.id"), nullable=False),
        sa.Column("previous_status", sa.String(), nullable=False),
        sa.Column("new_status", sa.String(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False, server_default="local-dev"),
        sa.Column("source", sa.String(), nullable=False, server_default="local-dev"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_outreach_draft_audit_draft_id", "outreach_draft_audit", ["draft_id"])


def downgrade():
    op.drop_index("ix_outreach_draft_audit_draft_id", table_name="outreach_draft_audit")
    op.drop_table("outreach_draft_audit")
