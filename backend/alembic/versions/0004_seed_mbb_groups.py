"""seed MBB competitor groups (McKinsey, BCG, Bain)

Revision ID: 0004_mbb
Revises: 0003_service_offering
Create Date: 2026-09-15

Adds the strategy-house peer group (MBB) so the dashboard can compare Accenture against
McKinsey, BCG and Bain distinctly from the Big 4. Category ``mbb`` is new.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_mbb"
down_revision: str | None = "0003_service_offering"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MBB = [
    ("mckinsey", "McKinsey & Company", "mbb", 17),
    ("bcg", "Boston Consulting Group", "mbb", 18),
    ("bain", "Bain & Company", "mbb", 19),
]


def upgrade() -> None:
    groups = sa.table(
        "competitor_groups",
        sa.column("slug", sa.Text),
        sa.column("label", sa.Text),
        sa.column("category", sa.Text),
        sa.column("display_order", sa.Integer),
    )
    op.bulk_insert(
        groups,
        [{"slug": s, "label": lbl, "category": c, "display_order": o} for (s, lbl, c, o) in MBB],
    )


def downgrade() -> None:
    slugs = tuple(s for (s, *_rest) in MBB)
    op.execute(
        sa.text("DELETE FROM competitor_groups WHERE slug IN :slugs").bindparams(
            sa.bindparam("slugs", slugs, expanding=True)
        )
    )
