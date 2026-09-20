"""enforce canonical source identity uniqueness

Revision ID: 0006
"""
from alembic import op


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        "uq_projects_source_source_id",
        "projects",
        ["source", "source_id"],
    )
    op.create_index(
        "ix_projects_source",
        "projects",
        ["source"],
    )
    op.create_index(
        "ix_projects_source_id",
        "projects",
        ["source_id"],
    )
    op.create_unique_constraint(
        "uq_contractors_source_source_id",
        "contractors",
        ["source", "source_id"],
    )
    op.create_index(
        "ix_contractors_source",
        "contractors",
        ["source"],
    )
    op.create_index(
        "ix_contractors_source_id",
        "contractors",
        ["source_id"],
    )


def downgrade():
    op.drop_index("ix_contractors_source_id", table_name="contractors")
    op.drop_index("ix_contractors_source", table_name="contractors")
    op.drop_constraint("uq_contractors_source_source_id", "contractors", type_="unique")
    op.drop_index("ix_projects_source_id", table_name="projects")
    op.drop_index("ix_projects_source", table_name="projects")
    op.drop_constraint("uq_projects_source_source_id", "projects", type_="unique")
