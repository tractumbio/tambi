"""add buyer division/branch (Defence org unit) to contracts

Revision ID: 0005_buyer_unit
Revises: 0004_mbb
Create Date: 2026-09-15

AusTender exposes the buyer's organisational unit on a party contactPoint
(division = group e.g. "CASG"/"ARMY"/"DSTG", branch = the specific command). This was
previously discarded; capturing it gives real Defence branch granularity.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_buyer_unit"
down_revision: str | None = "0004_mbb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("contracts", sa.Column("buyer_division", sa.Text(), nullable=True))
    op.add_column("contracts", sa.Column("buyer_branch", sa.Text(), nullable=True))
    op.create_index("ix_contracts_buyer_division", "contracts", ["buyer_division"])
    op.create_index("ix_contracts_buyer_branch", "contracts", ["buyer_branch"])


def downgrade() -> None:
    op.drop_index("ix_contracts_buyer_branch", table_name="contracts")
    op.drop_index("ix_contracts_buyer_division", table_name="contracts")
    op.drop_column("contracts", "buyer_branch")
    op.drop_column("contracts", "buyer_division")
