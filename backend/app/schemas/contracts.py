"""Response models for the contract data endpoints (spec Section 9)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class ContractListItem(BaseModel):
    ocid: str
    cn_id: str | None
    title: str | None
    buyer_name: str | None
    supplier_name: str | None
    competitor_slug: str | None
    competitor_label: str | None
    value_amount: float | None
    value_currency: str | None
    date_published: datetime | None
    period_end: date | None
    procurement_method: str | None
    is_defence: bool
    themes: list[str]


class ContractPage(BaseModel):
    items: list[ContractListItem]
    total: int
    limit: int
    offset: int


class AmendmentRelease(BaseModel):
    release_id: str
    release_date: datetime | None
    tags: list[str]
    source_file: str | None


class ContractDetail(BaseModel):
    ocid: str
    cn_id: str | None
    title: str | None
    description: str | None
    buyer_name: str | None
    supplier_name: str | None
    competitor_slug: str | None
    competitor_label: str | None
    value_amount: float | None
    value_currency: str | None
    date_published: datetime | None
    date_signed: datetime | None
    period_start: date | None
    period_end: date | None
    procurement_method: str | None
    unspsc_code: str | None
    unspsc_title: str | None
    is_defence: bool
    amendment_count: int
    themes: list[str]
    releases: list[AmendmentRelease]


class ThemeOption(BaseModel):
    slug: str
    label: str


class CompetitorOption(BaseModel):
    slug: str
    label: str
    category: str


class AgencyOption(BaseModel):
    id: int
    name: str


class ValueRange(BaseModel):
    min: float | None
    max: float | None


class DateRange(BaseModel):
    min: date | None
    max: date | None


class FilterOptions(BaseModel):
    themes: list[ThemeOption]
    competitors: list[CompetitorOption]
    agencies: list[AgencyOption]
    value_range: ValueRange
    date_range: DateRange
