"""create outreach drafts

Revision ID: 0008
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "outreach_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("match_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("match_records.id"), nullable=False),
        sa.Column("template_version", sa.String(), nullable=False),
        sa.Column("recipient_email", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("body", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="DRAFT"),
        sa.Column("generated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("provenance", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("match_id", "template_version", name="uq_outreach_drafts_match_template"),
    )
    op.create_index("ix_outreach_drafts_match_id", "outreach_drafts", ["match_id"])
    op.create_index("ix_outreach_drafts_status", "outreach_drafts", ["status"])


def downgrade():
    op.drop_index("ix_outreach_drafts_status", table_name="outreach_drafts")
    op.drop_index("ix_outreach_drafts_match_id", table_name="outreach_drafts")
    op.drop_table("outreach_drafts")
