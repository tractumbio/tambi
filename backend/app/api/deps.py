"""Shared API dependencies — the common filter set for dashboard endpoints.

Spec Section 9 requires the aggregate endpoints to accept one common filter set,
implemented once as a shared dependency rather than repeated per endpoint. Filters
are translated into SQLAlchemy WHERE conditions over ``Contract`` using correlated
subqueries, so applying them never multiplies rows (which would corrupt aggregates).

Every dashboard query is Defence-scoped by default — that is the market this product
covers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from fastapi import Query
from sqlalchemy import ColumnElement, and_, select

from app.models import CompetitorGroup, Contract, ContractTheme, Organisation, Theme

ACCENTURE_SLUG = "accenture"


@dataclass(frozen=True)
class CommonFilters:
    theme: str | None = None
    competitor: str | None = None
    agency_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    min_value: float | None = None
    max_value: float | None = None


def common_filters(
    theme: str | None = Query(None, description="Theme slug, e.g. 'defensive-cyber'"),
    competitor: str | None = Query(None, description="Competitor group slug, e.g. 'accenture'"),
    agency_id: int | None = Query(None, description="Buyer organisation id"),
    date_from: date | None = Query(None, description="Filter on date_published (inclusive)"),
    date_to: date | None = Query(None, description="Filter on date_published (exclusive)"),
    min_value: float | None = Query(None, description="Minimum contract value (AUD)"),
    max_value: float | None = Query(None, description="Maximum contract value (AUD)"),
) -> CommonFilters:
    return CommonFilters(
        theme=theme,
        competitor=competitor,
        agency_id=agency_id,
        date_from=date_from,
        date_to=date_to,
        min_value=min_value,
        max_value=max_value,
    )


def _as_dt(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


def contract_conditions(
    f: CommonFilters, *, defence_only: bool = True
) -> list[ColumnElement[bool]]:
    """Translate a filter set into WHERE conditions over ``Contract``.

    Theme and competitor filters use subqueries so the base contract query stays
    one row per ``ocid``.
    """
    conds: list[ColumnElement[bool]] = []
    if defence_only:
        conds.append(Contract.is_defence.is_(True))
    if f.date_from is not None:
        conds.append(Contract.date_published >= _as_dt(f.date_from))
    if f.date_to is not None:
        conds.append(Contract.date_published < _as_dt(f.date_to))
    if f.min_value is not None:
        conds.append(Contract.value_amount >= f.min_value)
    if f.max_value is not None:
        conds.append(Contract.value_amount <= f.max_value)
    if f.agency_id is not None:
        conds.append(Contract.buyer_org_id == f.agency_id)
    if f.competitor:
        supplier_ids = (
            select(Organisation.id)
            .join(CompetitorGroup, CompetitorGroup.id == Organisation.competitor_group_id)
            .where(CompetitorGroup.slug == f.competitor)
        )
        conds.append(Contract.supplier_org_id.in_(supplier_ids))
    if f.theme:
        theme_exists = (
            select(ContractTheme.id)
            .join(Theme, Theme.id == ContractTheme.theme_id)
            .where(and_(ContractTheme.ocid == Contract.ocid, Theme.slug == f.theme))
            .exists()
        )
        conds.append(theme_exists)
    return conds
