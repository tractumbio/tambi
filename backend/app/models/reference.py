"""Reference-project corpus for capability-match scoring.

A curated, editable set of past-project / capability descriptions per firm, used to
enrich the embedding centroids that opportunities are scored against. Kept deliberately
separate from ``contracts`` (awarded AusTender records) — these are capability reference
statements, not audited contract facts. Applied symmetrically across all firms so the
competitor comparison stays fair (no firm gets a data-richness advantage).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReferenceProject(Base):
    __tablename__ = "reference_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    firm_slug: Mapped[str] = mapped_column(Text, nullable=False)  # -> competitor_groups.slug
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    client: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)  # provenance note

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_reference_projects_firm", "firm_slug"),
    )
