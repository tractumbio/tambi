"""add knowledge_items table (accumulating market-intelligence knowledge base)

Revision ID: 0009_knowledge_items
Revises: 0008_monthly_reports
Create Date: 2026-09-15

Persistent, dedup'd store of every news/intelligence source the harvester discovers.
Accumulates over time (never deleted); first_seen_at drives change-since-last-report.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from alembic import op

revision: str = "0009_knowledge_items"
down_revision: str | None = "0008_monthly_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("url", sa.Text(), nullable=False, unique=True),
        sa.Column("headline", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("entities", ARRAY(sa.Text()), nullable=True),
        sa.Column("relevance", sa.Text(), nullable=True),
        sa.Column("published_date", sa.Date(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("source_query", sa.Text(), nullable=True),
        sa.Column("raw_path", sa.Text(), nullable=True),
        sa.Column("payload", JSONB(), nullable=True),
    )
    op.create_index("ix_knowledge_items_category", "knowledge_items", ["category"])
    op.create_index("ix_knowledge_items_first_seen", "knowledge_items", ["first_seen_at"])
    op.create_index("ix_knowledge_items_published", "knowledge_items", ["published_date"])


def downgrade() -> None:
    op.drop_table("knowledge_items")
