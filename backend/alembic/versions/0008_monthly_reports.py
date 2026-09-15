"""add monthly_reports table (Pillar III automated reporting)

Revision ID: 0008_monthly_reports
Revises: 0007_reference_projects
Create Date: 2026-09-15

Stores generated monthly market-intelligence reports, keyed by period window. The full
structured content lives in a JSONB payload so the report template can evolve without a
migration; scalar columns support listing, dedup and provenance.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0008_monthly_reports"
down_revision: str | None = "0007_reference_projects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "monthly_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("effort", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("contract_source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("news_source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_monthly_reports_period", "monthly_reports", ["period_start", "period_end"])
    op.create_index("ix_monthly_reports_generated", "monthly_reports", ["generated_at"])


def downgrade() -> None:
    op.drop_table("monthly_reports")
