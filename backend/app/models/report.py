"""Stored monthly market-intelligence reports (Pillar III).

One row per generated report, keyed by its period window. The full structured content
(all sections, findings, news, sources) lives in ``payload`` (JSONB) so the template can
evolve without a migration; the scalar columns are for listing, dedup and provenance.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MonthlyReport(Base):
    __tablename__ = "monthly_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")  # draft|published
    model: Mapped[str | None] = mapped_column(Text, nullable=True)
    effort: Mapped[str | None] = mapped_column(Text, nullable=True)

    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)  # full structured report

    contract_source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    news_source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_monthly_reports_period", "period_start", "period_end"),
        Index("ix_monthly_reports_generated", "generated_at"),
    )
