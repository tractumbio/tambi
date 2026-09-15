"""Response models for the dashboard metric endpoints (spec Section 9)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class SummaryKpis(BaseModel):
    period_start: date | None
    period_end: date | None
    total_value: float
    contract_count: int
    accenture_value: float
    accenture_share: float  # 0..1
    # Period-on-period deltas vs the immediately preceding window of equal length.
    total_value_delta_pct: float | None
    contract_count_delta_pct: float | None
    accenture_value_delta_pct: float | None


class SharePoint(BaseModel):
    bucket: date  # start of the month/quarter bucket
    competitor_slug: str
    competitor_label: str
    value: float


class ShareOverTime(BaseModel):
    granularity: str  # "month" | "quarter"
    points: list[SharePoint]


class ThemeBreakdownRow(BaseModel):
    theme_slug: str
    theme_label: str
    total_value: float
    contract_count: int
    accenture_value: float
    field_value: float


class CompetitorMomentumRow(BaseModel):
    competitor_slug: str
    competitor_label: str
    category: str
    value_12m: float
    count_12m: int
    value_prev_12m: float
    trend: str  # "up" | "down" | "flat"


class ExpiringContract(BaseModel):
    ocid: str
    cn_id: str | None
    title: str | None
    buyer_name: str | None
    supplier_name: str | None
    competitor_slug: str | None
    competitor_label: str | None
    value: float | None
    period_end: date | None
    days_to_expiry: int | None
    themes: list[str]


class AgencyBreakdownRow(BaseModel):
    agency_id: int
    agency_name: str
    total_value: float
    contract_count: int


# --- Accenture-addressable service offerings (ported from prior analytics) ---


class ServiceOfferingRow(BaseModel):
    service_offering: str
    total_value: float
    annualised_value: float  # value_per_year basis, used for market sizing
    contract_count: int
    accenture_value: float
    field_value: float


class AddressableSummary(BaseModel):
    fy_window: str
    total_defence_value: float
    addressable_value: float
    addressable_annualised: float
    addressable_count: int
    addressable_pct_of_defence: float  # 0..1
    accenture_value: float
    accenture_share_of_addressable: float  # 0..1


class GrowthPoint(BaseModel):
    fy_end_year: int
    fy_label: str  # e.g. "FY24"
    value: float  # annualised addressable value
    accenture_value: float
    yoy_pct: float | None  # vs prior FY


class GrowthResponse(BaseModel):
    service_offering: str | None  # None = all addressable
    points: list[GrowthPoint]
    cagr_pct: float | None  # compound annual growth across complete FYs
    latest_fy_value: float
    peak_fy_label: str | None


# --- Accenture vs peer cohorts (Big 4, MBB, challengers) ---


class PeerMember(BaseModel):
    slug: str
    label: str
    value: float
    contract_count: int


class PeerSeriesPoint(BaseModel):
    fy_end_year: int
    fy_label: str
    firms: dict[str, float]  # competitor-group slug -> value (Accenture + each cohort member)


class PeerComparison(BaseModel):
    cohort: str
    cohort_label: str
    basis: str  # "addressable" | "all-defence"
    accenture_value: float
    accenture_count: int
    cohort_value: float
    cohort_count: int
    accenture_share: float  # accenture / (accenture + cohort), 0..1
    members: list[PeerMember]
    series: list[PeerSeriesPoint]


# --- Supplier <-> agency relationship network ---


class NetworkNode(BaseModel):
    id: str
    label: str
    kind: str  # "competitor" | "agency" | "branch" | "theme"
    category: str | None  # competitor_group category, for competitor nodes
    slug: str | None  # competitor slug, for colouring
    value: float
    contract_count: int


class NetworkEdge(BaseModel):
    source: str  # competitor node id
    target: str  # agency node id
    value: float
    contract_count: int


class NetworkGraph(BaseModel):
    basis: str
    nodes: list[NetworkNode]
    edges: list[NetworkEdge]


class NetworkContractRow(BaseModel):
    ocid: str
    cn_id: str | None
    title: str | None
    description: str | None
    supplier_name: str | None
    competitor_slug: str | None
    competitor_label: str | None
    agency_name: str | None
    buyer_division: str | None
    buyer_branch: str | None
    value_amount: float | None
    value_currency: str | None
    value_per_year: float | None
    date_published: datetime | None
    date_signed: datetime | None
    period_start: date | None
    period_end: date | None
    procurement_method: str | None
    unspsc_code: str | None
    is_addressable: bool
    service_offering: str | None
    service_offering_confidence: int | None
    amendment_count: int
    themes: list[str]


class NetworkContracts(BaseModel):
    total: int
    limit: int
    items: list[NetworkContractRow]
