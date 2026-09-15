"""add service-offering / addressability / annualised-value fields to contracts

Revision ID: 0003_service_offering
Revises: 0002_seed
Create Date: 2026-09-15

Ports the previous-analytics concepts into the analytics layer: each contract carries
its Accenture-addressable service offering (one of five), an addressability flag, the
classifier confidence, and the annualised ("value per year") figure used for the
market-size and growth views.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_service_offering"
down_revision: str | None = "0002_seed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("contracts", sa.Column("service_offering", sa.Text(), nullable=True))
    op.add_column(
        "contracts",
        sa.Column("is_addressable", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "contracts", sa.Column("service_offering_confidence", sa.Integer(), nullable=True)
    )
    op.add_column(
        "contracts", sa.Column("value_per_year", sa.Numeric(18, 2), nullable=True)
    )
    op.create_index("ix_contracts_service_offering", "contracts", ["service_offering"])
    op.create_index("ix_contracts_is_addressable", "contracts", ["is_addressable"])
    op.create_index("ix_contracts_value_per_year", "contracts", ["value_per_year"])
    # Drives the addressable-market and service-offering breakdowns.
    op.create_index(
        "ix_contracts_addressable_offering",
        "contracts",
        ["is_addressable", "service_offering"],
    )


def downgrade() -> None:
    op.drop_index("ix_contracts_addressable_offering", table_name="contracts")
    op.drop_index("ix_contracts_value_per_year", table_name="contracts")
    op.drop_index("ix_contracts_is_addressable", table_name="contracts")
    op.drop_index("ix_contracts_service_offering", table_name="contracts")
    op.drop_column("contracts", "value_per_year")
    op.drop_column("contracts", "service_offering_confidence")
    op.drop_column("contracts", "is_addressable")
    op.drop_column("contracts", "service_offering")
