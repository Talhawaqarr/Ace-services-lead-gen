"""Phase 11 contractor raw ingestion table

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-20
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "raw_contractors",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="RECEIVED"),
        sa.Column("error_detail", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_unique_constraint(
        "uq_raw_contractors_source_source_id",
        "raw_contractors",
        ["source", "source_id"],
    )
    op.create_index("ix_raw_contractors_source", "raw_contractors", ["source"])
    op.create_index("ix_raw_contractors_status", "raw_contractors", ["status"])


def downgrade():
    op.drop_index("ix_raw_contractors_status", table_name="raw_contractors")
    op.drop_index("ix_raw_contractors_source", table_name="raw_contractors")
    op.drop_constraint(
        "uq_raw_contractors_source_source_id",
        "raw_contractors",
        type_="unique",
    )
    op.drop_table("raw_contractors")
