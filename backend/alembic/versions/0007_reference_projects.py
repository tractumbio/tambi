"""add reference_projects table (capability-match enrichment corpus)

Revision ID: 0007_reference_projects
Revises: 0006_atms
Create Date: 2026-09-15

Curated per-firm capability/project descriptions that enrich the embedding centroids
used to score opportunities. Applied symmetrically across all firms. Separate from
contracts — these are capability reference statements, not audited contract facts.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_reference_projects"
down_revision: str | None = "0006_atms"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reference_projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("firm_slug", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("client", sa.Text(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
    )
    op.create_index("ix_reference_projects_firm", "reference_projects", ["firm_slug"])


def downgrade() -> None:
    op.drop_table("reference_projects")
