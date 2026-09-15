"""initial schema — Phase 2 core tables

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-14

Creates the seven Phase 2 tables (spec Section 6) with single-column and composite
indexes. Hand-written (no live DB was available to autogenerate against); kept
in exact agreement with the ORM models in app/models.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "competitor_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "themes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "organisations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("abn", sa.Text(), nullable=True, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_normalised", sa.Text(), nullable=False),
        sa.Column("roles", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column(
            "competitor_group_id",
            sa.Integer(),
            sa.ForeignKey("competitor_groups.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_organisations_name_normalised", "organisations", ["name_normalised"])
    op.create_index("ix_organisations_abn", "organisations", ["abn"])

    op.create_table(
        "contracts",
        sa.Column("ocid", sa.Text(), primary_key=True),
        sa.Column("cn_id", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "buyer_org_id", sa.Integer(), sa.ForeignKey("organisations.id"), nullable=True
        ),
        sa.Column(
            "supplier_org_id", sa.Integer(), sa.ForeignKey("organisations.id"), nullable=True
        ),
        sa.Column("value_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("value_currency", sa.Text(), nullable=True),
        sa.Column("date_published", sa.DateTime(timezone=True), nullable=True),
        sa.Column("date_signed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("procurement_method", sa.Text(), nullable=True),
        sa.Column("unspsc_code", sa.Text(), nullable=True),
        sa.Column("unspsc_title", sa.Text(), nullable=True),
        sa.Column("is_defence", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("amendment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_release_id", sa.Text(), nullable=True),
    )
    op.create_index("ix_contracts_cn_id", "contracts", ["cn_id"])
    op.create_index("ix_contracts_supplier_org_id", "contracts", ["supplier_org_id"])
    op.create_index("ix_contracts_value_amount", "contracts", ["value_amount"])
    op.create_index("ix_contracts_date_published", "contracts", ["date_published"])
    op.create_index("ix_contracts_period_start", "contracts", ["period_start"])
    op.create_index("ix_contracts_period_end", "contracts", ["period_end"])
    op.create_index("ix_contracts_procurement_method", "contracts", ["procurement_method"])
    op.create_index("ix_contracts_unspsc_code", "contracts", ["unspsc_code"])
    op.create_index("ix_contracts_is_defence", "contracts", ["is_defence"])
    # Composite indexes for the dashboard query patterns (spec Section 6). DESC on the
    # trailing column matches the ORDER BY … DESC access pattern.
    op.create_index(
        "ix_contracts_defence_published",
        "contracts",
        ["is_defence", sa.text("date_published DESC")],
    )
    op.create_index("ix_contracts_defence_period_end", "contracts", ["is_defence", "period_end"])
    op.create_index(
        "ix_contracts_supplier_published",
        "contracts",
        ["supplier_org_id", sa.text("date_published DESC")],
    )
    op.create_index(
        "ix_contracts_defence_value",
        "contracts",
        ["is_defence", sa.text("value_amount DESC")],
    )

    op.create_table(
        "raw_releases",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ocid", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False, unique=True),
        sa.Column("release_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("source_file", sa.Text(), nullable=True),
    )
    op.create_index("ix_raw_releases_ocid", "raw_releases", ["ocid"])
    op.create_index("ix_raw_releases_release_date", "raw_releases", ["release_date"])

    op.create_table(
        "contract_themes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ocid",
            sa.Text(),
            sa.ForeignKey("contracts.ocid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("theme_id", sa.Integer(), sa.ForeignKey("themes.id"), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("method", sa.Text(), nullable=False),
    )
    op.create_index("ix_contract_themes_ocid", "contract_themes", ["ocid"])
    op.create_index(
        "uq_contract_themes_ocid_theme", "contract_themes", ["ocid", "theme_id"], unique=True
    )

    op.create_table(
        "ingest_state",
        sa.Column("job_name", sa.Text(), primary_key=True),
        sa.Column("last_release_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_status", sa.Text(), nullable=True),
        sa.Column("records_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("ingest_state")
    op.drop_table("contract_themes")
    op.drop_table("raw_releases")
    op.drop_table("contracts")
    op.drop_table("organisations")
    op.drop_table("themes")
    op.drop_table("competitor_groups")
