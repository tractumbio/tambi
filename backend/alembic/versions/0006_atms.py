"""add atms table (opportunity side — Approaches to Market)

Revision ID: 0006_atms
Revises: 0005_buyer_unit
Create Date: 2026-09-15

First of the §6.1 opportunity tables. ATMs are ingested from the AusTender ATM RSS
feed + detail pages (see ingest/README.md Phase 0.4.1). Kept separate from contracts.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_atms"
down_revision: str | None = "0005_buyer_unit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "atms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("atm_id", sa.Text(), nullable=False, unique=True),
        sa.Column("atm_uuid", sa.Text(), nullable=True),
        sa.Column("agency_org_id", sa.Integer(), sa.ForeignKey("organisations.id"), nullable=True),
        sa.Column("agency_name", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("atm_type", sa.Text(), nullable=True),
        sa.Column("unspsc_code", sa.Text(), nullable=True),
        sa.Column("unspsc_title", sa.Text(), nullable=True),
        sa.Column("published_date", sa.Date(), nullable=True),
        sa.Column("close_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location_state", sa.Text(), nullable=True),
        sa.Column("estimated_value", sa.Numeric(18, 2), nullable=True),
        sa.Column("is_defence", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("resulting_ocid", sa.Text(), nullable=True),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
    )
    op.create_index("ix_atms_atm_id", "atms", ["atm_id"])
    op.create_index("ix_atms_close_date", "atms", ["close_date"])
    op.create_index("ix_atms_unspsc_code", "atms", ["unspsc_code"])
    op.create_index("ix_atms_defence_close", "atms", ["is_defence", "close_date"])
    op.create_index("ix_atms_status", "atms", ["status"])


def downgrade() -> None:
    op.drop_table("atms")
