"""add news_domains table (user-editable reputable-source allowlist)

Revision ID: 0010_news_domains
Revises: 0009_knowledge_items
Create Date: 2026-09-15

The news harvester pulls only from these domains. Editable from the UI so an analyst can
add or remove reputable outlets without a code change.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_news_domains"
down_revision: str | None = "0009_knowledge_items"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "news_domains",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("domain", sa.Text(), nullable=False, unique=True),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
    )


def downgrade() -> None:
    op.drop_table("news_domains")
