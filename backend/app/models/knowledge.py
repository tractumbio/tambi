"""Accumulating market-intelligence knowledge base (Pillar III).

Every source discovered by the news harvester is stored here exactly once (dedup on
``url``) and never deleted, so the corpus grows over time. ``first_seen_at`` is the
accumulation clock: it lets a report say how much new intelligence has arrived since the
last one. Raw source snapshots live on disk (``raw_path``); this table holds the
structured, queryable metadata.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NewsDomain(Base):
    """User-editable allowlist of reputable outlets the harvester may pull from."""

    __tablename__ = "news_domains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    domain: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(Text, nullable=False)  # competitor|government|macro
    entities: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)  # competitor slugs
    relevance: Mapped[str | None] = mapped_column(Text, nullable=True)

    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    source_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_path: Mapped[str | None] = mapped_column(Text, nullable=True)  # disk archive file
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_knowledge_items_category", "category"),
        Index("ix_knowledge_items_first_seen", "first_seen_at"),
        Index("ix_knowledge_items_published", "published_date"),
    )
