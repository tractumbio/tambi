"""Request/response models for Pillar III — monthly market-intelligence reports."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class GenerateReportRequest(BaseModel):
    # Either month (YYYY-MM) or an explicit window; both optional -> previous calendar month.
    month: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    model: str | None = None
    effort: str | None = None
    structure: str | None = None


class MonthlyReportSummary(BaseModel):
    id: int
    period_start: date
    period_end: date
    generated_at: datetime
    status: str
    model: str | None
    effort: str | None
    title: str | None
    contract_source_count: int
    news_source_count: int


class MonthlyReportOut(MonthlyReportSummary):
    executive_summary: str | None
    payload: dict
