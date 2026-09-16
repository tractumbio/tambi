"""add feedback table for user-submitted feedback

Revision ID: 0011_feedback
Revises: 0010_news_domains
Create Date: 2026-09-16

Stores free-text feedback submitted by users, including the submission
timestamp and optional user-agent string for context.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011_feedback"
down_revision: str | None = "0010_news_domains"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("feedback")
