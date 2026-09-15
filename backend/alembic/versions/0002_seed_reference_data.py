"""seed reference data — themes and competitor groups

Revision ID: 0002_seed
Revises: 0001_initial
Create Date: 2026-09-14

Seeds the five Defence themes and the competitor group taxonomy (spec Section 6).
Reference data lives in a migration so a fresh ``alembic upgrade head`` yields a
ready-to-use database and re-running is deterministic.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_seed"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


THEMES = [
    (
        "nuclear-submarines",
        "Nuclear Submarines",
        "AUKUS Pillar I: nuclear-powered submarine programme, build, sustainment and "
        "enabling infrastructure.",
        1,
    ),
    (
        "workforce",
        "Workforce",
        "Defence workforce growth, skilling, recruitment and retention across the enterprise.",
        2,
    ),
    (
        "defensive-cyber",
        "Defensive Cyber",
        "Defensive cyber operations, security operations, network defence and resilience.",
        3,
    ),
    (
        "decision-advantage",
        "Decision Advantage",
        "Command, control, intelligence, data and AI-enabled decision superiority.",
        4,
    ),
    (
        "digital-engineering",
        "Digital Engineering",
        "Model-based systems engineering, digital twins and digital-thread capability.",
        5,
    ),
]

COMPETITOR_GROUPS = [
    ("accenture", "Accenture", "accenture", 1),
    ("deloitte", "Deloitte", "big4", 2),
    ("pwc", "PwC", "big4", 3),
    ("kpmg", "KPMG", "big4", 4),
    ("ey", "EY", "big4", 5),
    ("ibm", "IBM", "sys_integrator", 6),
    ("dxc", "DXC Technology", "sys_integrator", 7),
    ("leidos", "Leidos", "sys_integrator", 8),
    ("lockheed-martin", "Lockheed Martin", "defence_prime", 9),
    ("bae-systems", "BAE Systems", "defence_prime", 10),
    ("thales", "Thales", "defence_prime", 11),
    ("boeing-defence", "Boeing Defence", "defence_prime", 12),
    ("babcock", "Babcock", "defence_prime", 13),
    ("kbr", "KBR", "consulting", 14),
    ("jacobs", "Jacobs", "consulting", 15),
    ("nova-systems", "Nova Systems", "sme", 16),
    ("other", "Other", "other", 99),
]


def upgrade() -> None:
    themes = sa.table(
        "themes",
        sa.column("slug", sa.Text),
        sa.column("label", sa.Text),
        sa.column("description", sa.Text),
        sa.column("display_order", sa.Integer),
    )
    op.bulk_insert(
        themes,
        [
            {"slug": s, "label": lbl, "description": desc, "display_order": order}
            for (s, lbl, desc, order) in THEMES
        ],
    )

    groups = sa.table(
        "competitor_groups",
        sa.column("slug", sa.Text),
        sa.column("label", sa.Text),
        sa.column("category", sa.Text),
        sa.column("display_order", sa.Integer),
    )
    op.bulk_insert(
        groups,
        [
            {"slug": s, "label": lbl, "category": cat, "display_order": order}
            for (s, lbl, cat, order) in COMPETITOR_GROUPS
        ],
    )


def downgrade() -> None:
    theme_slugs = tuple(s for (s, *_rest) in THEMES)
    group_slugs = tuple(s for (s, *_rest) in COMPETITOR_GROUPS)
    op.execute(
        sa.text("DELETE FROM themes WHERE slug IN :slugs").bindparams(
            sa.bindparam("slugs", theme_slugs, expanding=True)
        )
    )
    op.execute(
        sa.text("DELETE FROM competitor_groups WHERE slug IN :slugs").bindparams(
            sa.bindparam("slugs", group_slugs, expanding=True)
        )
    )
