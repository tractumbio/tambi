"""Dashboard aggregate endpoints (spec Section 9, ``api/metrics``).

All endpoints are Defence-scoped and share the common filter set from
``app.api.deps``. Money is summed from ``contracts.value_amount`` (AUD); the LLM
layer is not involved here — these are plain SQL aggregates.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Integer, Numeric, case, cast, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import ACCENTURE_SLUG, CommonFilters, common_filters, contract_conditions
from app.db.session import get_db
from app.models import CompetitorGroup, Contract, ContractTheme, Organisation, Theme
from app.processing.themes import DEFENCE_BUYER_NORMALISED
from app.schemas.metrics import (
    AddressableSummary,
    AgencyBreakdownRow,
    CompetitorMomentumRow,
    ExpiringContract,
    GrowthPoint,
    GrowthResponse,
    NetworkContractRow,
    NetworkContracts,
    NetworkEdge,
    NetworkGraph,
    NetworkNode,
    PeerComparison,
    PeerMember,
    PeerSeriesPoint,
    ServiceOfferingRow,
    ShareOverTime,
    SharePoint,
    SummaryKpis,
    ThemeBreakdownRow,
)

# Peer cohorts for the Accenture-vs-field comparisons (by competitor_groups.category).
PEER_COHORTS: dict[str, tuple[str, set[str]]] = {
    "big4": ("Big 4", {"big4"}),
    "mbb": ("MBB (McKinsey, BCG, Bain)", {"mbb"}),
    "challengers": ("SIs & Challengers", {"sys_integrator", "consulting", "sme"}),
}

router = APIRouter(prefix="/metrics", tags=["metrics"])

_MONEY = Numeric(18, 2)


def _accenture_supplier_ids():
    return (
        select(Organisation.id)
        .join(CompetitorGroup, CompetitorGroup.id == Organisation.competitor_group_id)
        .where(CompetitorGroup.slug == ACCENTURE_SLUG)
    )


def _delta_pct(current: float, previous: float) -> float | None:
    if previous <= 0:
        return None
    return round((current - previous) / previous * 100, 1)


def _latest_defence_date(session: Session) -> date | None:
    latest = session.execute(
        select(func.max(Contract.date_published)).where(Contract.is_defence.is_(True))
    ).scalar()
    return latest.date() if latest else None


@router.get("/summary", response_model=SummaryKpis)
def get_summary(
    f: CommonFilters = Depends(common_filters), session: Session = Depends(get_db)
) -> SummaryKpis:
    """Headline KPIs for the period, with period-on-period deltas."""
    end = f.date_to or _latest_defence_date(session) or date.today()
    start = f.date_from or (end - timedelta(days=365))
    span = end - start
    prev_end, prev_start = start, start - span

    def aggregate(win_start: date, win_end: date) -> tuple[float, int, float]:
        win = CommonFilters(
            theme=f.theme,
            competitor=f.competitor,
            agency_id=f.agency_id,
            date_from=win_start,
            date_to=win_end,
            min_value=f.min_value,
            max_value=f.max_value,
        )
        conds = contract_conditions(win)
        total_value, count = session.execute(
            select(func.coalesce(func.sum(Contract.value_amount), 0), func.count()).where(*conds)
        ).one()
        acc_value = session.execute(
            select(func.coalesce(func.sum(Contract.value_amount), 0)).where(
                *conds, Contract.supplier_org_id.in_(_accenture_supplier_ids())
            )
        ).scalar_one()
        return float(total_value), int(count), float(acc_value)

    total_value, count, acc_value = aggregate(start, end)
    prev_value, prev_count, prev_acc = aggregate(prev_start, prev_end)

    return SummaryKpis(
        period_start=start,
        period_end=end,
        total_value=total_value,
        contract_count=count,
        accenture_value=acc_value,
        accenture_share=round(acc_value / total_value, 4) if total_value > 0 else 0.0,
        total_value_delta_pct=_delta_pct(total_value, prev_value),
        contract_count_delta_pct=_delta_pct(count, prev_count),
        accenture_value_delta_pct=_delta_pct(acc_value, prev_acc),
    )


@router.get("/share-over-time", response_model=ShareOverTime)
def get_share_over_time(
    f: CommonFilters = Depends(common_filters),
    granularity: str = Query("month", pattern="^(month|quarter)$"),
    session: Session = Depends(get_db),
) -> ShareOverTime:
    """Defence contract value by competitor group over time."""
    conds = contract_conditions(f)
    bucket = func.date_trunc(granularity, Contract.date_published).label("bucket")
    slug = func.coalesce(CompetitorGroup.slug, "other").label("slug")
    label = func.coalesce(CompetitorGroup.label, "Other").label("label")

    rows = session.execute(
        select(bucket, slug, label, func.coalesce(func.sum(Contract.value_amount), 0))
        .select_from(Contract)
        .outerjoin(Organisation, Organisation.id == Contract.supplier_org_id)
        .outerjoin(CompetitorGroup, CompetitorGroup.id == Organisation.competitor_group_id)
        .where(*conds, Contract.date_published.is_not(None))
        .group_by(bucket, slug, label)
        .order_by(bucket)
    ).all()

    points = [
        SharePoint(
            bucket=r.bucket.date() if hasattr(r.bucket, "date") else r.bucket,
            competitor_slug=r.slug,
            competitor_label=r.label,
            value=float(r[3]),
        )
        for r in rows
    ]
    return ShareOverTime(granularity=granularity, points=points)


@router.get("/by-theme", response_model=list[ThemeBreakdownRow])
def get_by_theme(
    f: CommonFilters = Depends(common_filters), session: Session = Depends(get_db)
) -> list[ThemeBreakdownRow]:
    """Value and count per theme, split Accenture vs the rest of the field."""
    conds = contract_conditions(f)
    is_accenture = case((CompetitorGroup.slug == ACCENTURE_SLUG, Contract.value_amount), else_=0)

    rows = session.execute(
        select(
            Theme.slug,
            Theme.label,
            func.coalesce(func.sum(Contract.value_amount), 0).label("total_value"),
            func.count(func.distinct(Contract.ocid)).label("contract_count"),
            func.coalesce(func.sum(cast(is_accenture, _MONEY)), 0).label("accenture_value"),
        )
        .select_from(Contract)
        .join(ContractTheme, ContractTheme.ocid == Contract.ocid)
        .join(Theme, Theme.id == ContractTheme.theme_id)
        .outerjoin(Organisation, Organisation.id == Contract.supplier_org_id)
        .outerjoin(CompetitorGroup, CompetitorGroup.id == Organisation.competitor_group_id)
        .where(*conds)
        .group_by(Theme.slug, Theme.label, Theme.display_order)
        .order_by(Theme.display_order)
    ).all()

    return [
        ThemeBreakdownRow(
            theme_slug=r.slug,
            theme_label=r.label,
            total_value=float(r.total_value),
            contract_count=int(r.contract_count),
            accenture_value=float(r.accenture_value),
            field_value=float(r.total_value) - float(r.accenture_value),
        )
        for r in rows
    ]


@router.get("/competitor-momentum", response_model=list[CompetitorMomentumRow])
def get_competitor_momentum(
    f: CommonFilters = Depends(common_filters), session: Session = Depends(get_db)
) -> list[CompetitorMomentumRow]:
    """Rolling 12-month value/count per competitor group, with trend direction."""
    anchor = _latest_defence_date(session) or date.today()
    start_12 = datetime(anchor.year, anchor.month, anchor.day, tzinfo=UTC) - timedelta(days=365)
    start_24 = start_12 - timedelta(days=365)

    conds = contract_conditions(f, defence_only=True)
    v12 = case((Contract.date_published >= start_12, Contract.value_amount), else_=0)
    c12 = case((Contract.date_published >= start_12, 1), else_=0)
    v_prev = case(
        (
            (Contract.date_published >= start_24) & (Contract.date_published < start_12),
            Contract.value_amount,
        ),
        else_=0,
    )

    rows = session.execute(
        select(
            CompetitorGroup.slug,
            CompetitorGroup.label,
            CompetitorGroup.category,
            func.coalesce(func.sum(cast(v12, _MONEY)), 0).label("v12"),
            func.coalesce(func.sum(c12), 0).label("c12"),
            func.coalesce(func.sum(cast(v_prev, _MONEY)), 0).label("vprev"),
        )
        .select_from(Contract)
        .join(Organisation, Organisation.id == Contract.supplier_org_id)
        .join(CompetitorGroup, CompetitorGroup.id == Organisation.competitor_group_id)
        .where(*conds, Contract.date_published >= start_24)
        .group_by(CompetitorGroup.slug, CompetitorGroup.label, CompetitorGroup.category,
                  CompetitorGroup.display_order)
        .order_by(func.coalesce(func.sum(cast(v12, _MONEY)), 0).desc())
    ).all()

    result: list[CompetitorMomentumRow] = []
    for r in rows:
        v12v, vprev = float(r.v12), float(r.vprev)
        if v12v > vprev * 1.05:
            trend = "up"
        elif v12v < vprev * 0.95:
            trend = "down"
        else:
            trend = "flat"
        result.append(
            CompetitorMomentumRow(
                competitor_slug=r.slug,
                competitor_label=r.label,
                category=r.category,
                value_12m=v12v,
                count_12m=int(r.c12),
                value_prev_12m=vprev,
                trend=trend,
            )
        )
    return result


@router.get("/expiring", response_model=list[ExpiringContract])
def get_expiring(
    f: CommonFilters = Depends(common_filters),
    within_days: int = Query(365, ge=1, le=1825, description="Forward expiry window in days"),
    exclude_accenture: bool = Query(False, description="Show only competitor-held contracts"),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_db),
) -> list[ExpiringContract]:
    """Contracts expiring in a forward window — the recompete pipeline."""
    today = date.today()
    horizon = today + timedelta(days=within_days)
    conds = contract_conditions(f)

    supplier = Organisation.__table__.alias("supplier_org")
    buyer = Organisation.__table__.alias("buyer_org")
    theme_agg = (
        select(func.array_agg(Theme.slug))
        .select_from(ContractTheme)
        .join(Theme, Theme.id == ContractTheme.theme_id)
        .where(ContractTheme.ocid == Contract.ocid)
        .scalar_subquery()
    )

    stmt = (
        select(
            Contract.ocid,
            Contract.cn_id,
            Contract.title,
            Contract.value_amount,
            Contract.period_end,
            buyer.c.name.label("buyer_name"),
            supplier.c.name.label("supplier_name"),
            CompetitorGroup.slug.label("competitor_slug"),
            CompetitorGroup.label.label("competitor_label"),
            theme_agg.label("themes"),
        )
        .select_from(Contract)
        .outerjoin(buyer, buyer.c.id == Contract.buyer_org_id)
        .outerjoin(supplier, supplier.c.id == Contract.supplier_org_id)
        .outerjoin(CompetitorGroup, CompetitorGroup.id == supplier.c.competitor_group_id)
        .where(*conds, Contract.period_end >= today, Contract.period_end <= horizon)
        .order_by(Contract.value_amount.desc().nullslast())
        .limit(limit)
    )
    if exclude_accenture:
        stmt = stmt.where(
            (CompetitorGroup.slug != ACCENTURE_SLUG) | (CompetitorGroup.slug.is_(None))
        )

    rows = session.execute(stmt).all()
    return [
        ExpiringContract(
            ocid=r.ocid,
            cn_id=r.cn_id,
            title=r.title,
            buyer_name=r.buyer_name,
            supplier_name=r.supplier_name,
            competitor_slug=r.competitor_slug,
            competitor_label=r.competitor_label,
            value=float(r.value_amount) if r.value_amount is not None else None,
            period_end=r.period_end,
            days_to_expiry=(r.period_end - today).days if r.period_end else None,
            themes=list(r.themes) if r.themes else [],
        )
        for r in rows
    ]


# --- Accenture-addressable service offerings & growth (ported from prior analytics) ---


def _current_fy_start_year(today: date) -> int:
    """Australian financial year starts 1 July; return the calendar year it starts in."""
    return today.year if today.month >= 7 else today.year - 1


def _fy_window_from(window: str, today: date) -> date | None:
    """Lower date bound (on date_published) for a named FY window, or None for 'all'."""
    start_year = _current_fy_start_year(today)
    if window == "current":
        return date(start_year, 7, 1)
    if window == "last3":
        return date(start_year - 2, 7, 1)
    if window == "last5":
        return date(start_year - 4, 7, 1)
    return None  # "all"


def _fy_end_year_expr():
    """SQL: financial-year end year of date_published (e.g. Aug 2025 -> 2026)."""
    return cast(
        func.extract("year", Contract.date_published)
        + case((func.extract("month", Contract.date_published) >= 7, 1), else_=0),
        Integer,
    )


@router.get("/service-offerings", response_model=list[ServiceOfferingRow])
def get_service_offerings(
    f: CommonFilters = Depends(common_filters),
    fy_window: str = Query("all", pattern="^(all|last3|last5|current)$"),
    session: Session = Depends(get_db),
) -> list[ServiceOfferingRow]:
    """Accenture-addressable value by service offering, Accenture vs field."""
    conds = contract_conditions(f)
    lower = _fy_window_from(fy_window, date.today())
    if lower is not None:
        conds = [*conds, Contract.date_published >= datetime(lower.year, lower.month, lower.day,
                 tzinfo=UTC)]
    acc_val = case((CompetitorGroup.slug == ACCENTURE_SLUG, Contract.value_amount), else_=0)

    rows = session.execute(
        select(
            Contract.service_offering,
            func.coalesce(func.sum(Contract.value_amount), 0).label("total_value"),
            func.coalesce(func.sum(Contract.value_per_year), 0).label("annualised"),
            func.count().label("n"),
            func.coalesce(func.sum(cast(acc_val, _MONEY)), 0).label("accenture_value"),
        )
        .select_from(Contract)
        .outerjoin(Organisation, Organisation.id == Contract.supplier_org_id)
        .outerjoin(CompetitorGroup, CompetitorGroup.id == Organisation.competitor_group_id)
        .where(*conds, Contract.is_addressable.is_(True), Contract.service_offering.is_not(None))
        .group_by(Contract.service_offering)
        .order_by(func.coalesce(func.sum(Contract.value_amount), 0).desc())
    ).all()

    return [
        ServiceOfferingRow(
            service_offering=r.service_offering,
            total_value=float(r.total_value),
            annualised_value=float(r.annualised),
            contract_count=int(r.n),
            accenture_value=float(r.accenture_value),
            field_value=float(r.total_value) - float(r.accenture_value),
        )
        for r in rows
    ]


@router.get("/addressable-summary", response_model=AddressableSummary)
def get_addressable_summary(
    f: CommonFilters = Depends(common_filters),
    fy_window: str = Query("all", pattern="^(all|last3|last5|current)$"),
    session: Session = Depends(get_db),
) -> AddressableSummary:
    """Headline Accenture-addressable market KPIs within a FY window."""
    base = contract_conditions(f)
    lower = _fy_window_from(fy_window, date.today())
    if lower is not None:
        base = [*base, Contract.date_published >= datetime(lower.year, lower.month, lower.day,
                tzinfo=UTC)]

    total_defence = session.execute(
        select(func.coalesce(func.sum(Contract.value_amount), 0)).where(*base)
    ).scalar_one()

    addr_conds = [*base, Contract.is_addressable.is_(True)]
    addr_value, addr_annualised, addr_count = session.execute(
        select(
            func.coalesce(func.sum(Contract.value_amount), 0),
            func.coalesce(func.sum(Contract.value_per_year), 0),
            func.count(),
        ).where(*addr_conds)
    ).one()
    accenture_value = session.execute(
        select(func.coalesce(func.sum(Contract.value_amount), 0)).where(
            *addr_conds, Contract.supplier_org_id.in_(_accenture_supplier_ids())
        )
    ).scalar_one()

    total_defence = float(total_defence)
    addr_value = float(addr_value)
    accenture_value = float(accenture_value)
    return AddressableSummary(
        fy_window=fy_window,
        total_defence_value=total_defence,
        addressable_value=addr_value,
        addressable_annualised=float(addr_annualised),
        addressable_count=int(addr_count),
        addressable_pct_of_defence=round(addr_value / total_defence, 4) if total_defence else 0.0,
        accenture_value=accenture_value,
        accenture_share_of_addressable=(
            round(accenture_value / addr_value, 4) if addr_value else 0.0
        ),
    )


@router.get("/growth", response_model=GrowthResponse)
def get_growth(
    f: CommonFilters = Depends(common_filters),
    offering: str | None = Query(None, description="Restrict to one service offering"),
    session: Session = Depends(get_db),
) -> GrowthResponse:
    """Annualised addressable value by financial year, with YoY and CAGR."""
    conds = [*contract_conditions(f), Contract.is_addressable.is_(True)]
    if offering:
        conds.append(Contract.service_offering == offering)

    fy = _fy_end_year_expr().label("fy")
    acc_val = case((CompetitorGroup.slug == ACCENTURE_SLUG, Contract.value_per_year), else_=0)
    rows = session.execute(
        select(
            fy,
            func.coalesce(func.sum(Contract.value_per_year), 0).label("value"),
            func.coalesce(func.sum(cast(acc_val, _MONEY)), 0).label("accenture_value"),
        )
        .select_from(Contract)
        .outerjoin(Organisation, Organisation.id == Contract.supplier_org_id)
        .outerjoin(CompetitorGroup, CompetitorGroup.id == Organisation.competitor_group_id)
        .where(*conds, Contract.date_published.is_not(None))
        .group_by(fy)
        .order_by(fy)
    ).all()

    points: list[GrowthPoint] = []
    prev: float | None = None
    for r in rows:
        value = float(r.value)
        yoy = None if prev is None or prev <= 0 else round((value - prev) / prev * 100, 1)
        points.append(
            GrowthPoint(
                fy_end_year=int(r.fy),
                fy_label=f"FY{int(r.fy) % 100:02d}",
                value=value,
                accenture_value=float(r.accenture_value),
                yoy_pct=yoy,
            )
        )
        prev = value

    # CAGR across complete financial years only (exclude the current partial FY).
    current_fy_end = _current_fy_start_year(date.today()) + 1
    complete = [p for p in points if p.fy_end_year < current_fy_end and p.value > 0]
    cagr = None
    if len(complete) >= 2:
        first, last = complete[0].value, complete[-1].value
        span = complete[-1].fy_end_year - complete[0].fy_end_year
        if first > 0 and span > 0:
            cagr = round(((last / first) ** (1 / span) - 1) * 100, 1)

    peak = max(points, key=lambda p: p.value, default=None)
    return GrowthResponse(
        service_offering=offering,
        points=points,
        cagr_pct=cagr,
        latest_fy_value=points[-1].value if points else 0.0,
        peak_fy_label=peak.fy_label if peak else None,
    )


@router.get("/peer-comparison", response_model=PeerComparison)
def get_peer_comparison(
    f: CommonFilters = Depends(common_filters),
    cohort: str = Query("big4", pattern="^(big4|mbb|challengers)$"),
    addressable_only: bool = Query(True, description="Compare on the addressable market only"),
    session: Session = Depends(get_db),
) -> PeerComparison:
    """Accenture vs a peer cohort (Big 4, MBB, or SIs & challengers)."""
    label, categories = PEER_COHORTS[cohort]
    conds = contract_conditions(f)
    if addressable_only:
        conds = [*conds, Contract.is_addressable.is_(True)]

    def _grouped():
        return (
            select(Contract)
            .join(Organisation, Organisation.id == Contract.supplier_org_id)
            .join(CompetitorGroup, CompetitorGroup.id == Organisation.competitor_group_id)
        )

    is_accenture = CompetitorGroup.slug == ACCENTURE_SLUG
    is_cohort = CompetitorGroup.category.in_(categories)

    acc_value, acc_count = session.execute(
        _grouped()
        .with_only_columns(func.coalesce(func.sum(Contract.value_amount), 0), func.count())
        .where(*conds, is_accenture)
    ).one()
    coh_value, coh_count = session.execute(
        _grouped()
        .with_only_columns(func.coalesce(func.sum(Contract.value_amount), 0), func.count())
        .where(*conds, is_cohort)
    ).one()

    member_rows = session.execute(
        _grouped()
        .with_only_columns(
            CompetitorGroup.slug,
            CompetitorGroup.label,
            func.coalesce(func.sum(Contract.value_amount), 0).label("value"),
            func.count().label("n"),
        )
        .where(*conds, is_cohort)
        .group_by(CompetitorGroup.slug, CompetitorGroup.label, CompetitorGroup.display_order)
        .order_by(func.coalesce(func.sum(Contract.value_amount), 0).desc())
    ).all()

    # Per-firm FY series (Accenture + each cohort member) so the UI can draw one line
    # per firm. Fill missing (firm, FY) combinations with 0 for continuous lines.
    fy = _fy_end_year_expr().label("fy")
    series_rows = session.execute(
        _grouped()
        .with_only_columns(
            fy,
            CompetitorGroup.slug.label("slug"),
            func.coalesce(func.sum(Contract.value_amount), 0).label("value"),
        )
        .where(*conds, or_(is_accenture, is_cohort), Contract.date_published.is_not(None))
        .group_by(fy, CompetitorGroup.slug)
        .order_by(fy)
    ).all()

    firm_slugs = [ACCENTURE_SLUG, *[r.slug for r in member_rows if float(r.value) > 0]]
    by_fy: dict[int, dict[str, float]] = {}
    for r in series_rows:
        by_fy.setdefault(int(r.fy), {})[r.slug] = float(r.value)
    series = [
        PeerSeriesPoint(
            fy_end_year=year,
            fy_label=f"FY{year % 100:02d}",
            firms={slug: values.get(slug, 0.0) for slug in firm_slugs},
        )
        for year, values in sorted(by_fy.items())
    ]

    acc_value, coh_value = float(acc_value), float(coh_value)
    denom = acc_value + coh_value
    return PeerComparison(
        cohort=cohort,
        cohort_label=label,
        basis="addressable" if addressable_only else "all-defence",
        accenture_value=acc_value,
        accenture_count=int(acc_count),
        cohort_value=coh_value,
        cohort_count=int(coh_count),
        accenture_share=round(acc_value / denom, 4) if denom else 0.0,
        members=[
            PeerMember(
                slug=r.slug, label=r.label, value=float(r.value), contract_count=int(r.n)
            )
            for r in member_rows
            if float(r.value) > 0
        ],
        series=series,
    )


@router.get("/network", response_model=NetworkGraph)
def get_network(
    f: CommonFilters = Depends(common_filters),
    addressable_only: bool = Query(False, description="Restrict to the addressable market"),
    immediate_only: bool = Query(
        True, description="Only Accenture's immediate competition (exclude Defence primes)"
    ),
    hub: str = Query("branch", pattern="^(branch|agency)$", description="Hub layer"),
    agency_limit: int = Query(14, ge=3, le=40, description="Top-N hubs by value"),
    include_themes: bool = Query(False, description="Add Defence capability-area (theme) nodes"),
    session: Session = Depends(get_db),
) -> NetworkGraph:
    """Supplier <-> Defence-agency (and capability-area) relationship network.

    Nodes are named competitor groups (excluding ``other``), the top buyer agencies, and —
    when ``include_themes`` is set — the Defence capability themes that stand in for
    agency branches (the OCDS feed carries no branch/division, only the agency). Edges are
    the aggregated contract value linking a competitor to an agency or a capability area.
    """
    conds = contract_conditions(f)
    if addressable_only:
        conds = [*conds, Contract.is_addressable.is_(True)]

    # Which competitor groups count. Always drop the 'other' bucket; when immediate_only
    # is set, also drop Defence platform primes (not Accenture's immediate competition).
    comp_conds = [CompetitorGroup.slug != "other"]
    if immediate_only:
        comp_conds = [*comp_conds, CompetitorGroup.category != "defence_prime"]

    buyer = Organisation.__table__.alias("buyer_org")
    # Restrict to Defence-portfolio buyers only (Department of Defence, ASD, DSTG,
    # Australian Submarine Agency, CASG, Army/Navy/Air Force, ...) — never other
    # departments, even when is_defence fired on UNSPSC/keyword for a non-Defence buyer.
    defence_buyer = or_(
        buyer.c.name_normalised.in_(list(DEFENCE_BUYER_NORMALISED)),
        buyer.c.name_normalised.like("%defence%"),
    )
    # Hub dimension: real Defence branch (buyer_division, falling back to the agency name)
    # or the top-level agency. This is the Defence branch data recovered from ingestion.
    hub_expr = (
        func.coalesce(Contract.buyer_division, buyer.c.name)
        if hub == "branch"
        else buyer.c.name
    ).label("hub")
    hub_kind = "branch" if hub == "branch" else "agency"

    edge_rows = session.execute(
        select(
            CompetitorGroup.slug,
            CompetitorGroup.label,
            CompetitorGroup.category,
            hub_expr,
            func.coalesce(func.sum(Contract.value_amount), 0).label("value"),
            func.count().label("n"),
        )
        .select_from(Contract)
        .join(Organisation, Organisation.id == Contract.supplier_org_id)
        .join(CompetitorGroup, CompetitorGroup.id == Organisation.competitor_group_id)
        .join(buyer, buyer.c.id == Contract.buyer_org_id)
        .where(*conds, *comp_conds, defence_buyer)
        .group_by(CompetitorGroup.slug, CompetitorGroup.label, CompetitorGroup.category, hub_expr)
    ).all()

    # Keep only the top hubs by total value flowing to named competitors.
    hub_totals: dict[str, float] = {}
    for r in edge_rows:
        if r.hub:
            hub_totals[r.hub] = hub_totals.get(r.hub, 0.0) + float(r.value)
    top_hubs = {
        h for h, _ in sorted(hub_totals.items(), key=lambda kv: kv[1], reverse=True)[:agency_limit]
    }
    kept = [r for r in edge_rows if r.hub in top_hubs and float(r.value) > 0]

    comp_agg: dict[str, dict[str, Any]] = {}
    hub_agg: dict[str, dict[str, Any]] = {}
    edges: list[NetworkEdge] = []
    for r in kept:
        edges.append(
            NetworkEdge(
                source=f"c:{r.slug}", target=f"h:{r.hub}",
                value=float(r.value), contract_count=int(r.n),
            )
        )
        c = comp_agg.setdefault(
            r.slug, {"label": r.label, "category": r.category, "value": 0.0, "n": 0}
        )
        c["value"] += float(r.value)
        c["n"] += int(r.n)
        h = hub_agg.setdefault(r.hub, {"value": 0.0, "n": 0})
        h["value"] += float(r.value)
        h["n"] += int(r.n)

    nodes = [
        NetworkNode(
            id=f"c:{slug}", label=c["label"], kind="competitor",
            category=c["category"], slug=slug, value=c["value"], contract_count=c["n"],
        )
        for slug, c in comp_agg.items()
    ] + [
        NetworkNode(
            id=f"h:{name}", label=name, kind=hub_kind,
            category=None, slug=None, value=h["value"], contract_count=h["n"],
        )
        for name, h in hub_agg.items()
    ]

    # Capability-area (theme) layer — the available proxy for Defence branches.
    if include_themes:
        theme_rows = session.execute(
            select(
                CompetitorGroup.slug.label("cslug"),
                Theme.slug.label("tslug"),
                Theme.label.label("tlabel"),
                func.coalesce(func.sum(Contract.value_amount), 0).label("value"),
                func.count().label("n"),
            )
            .select_from(Contract)
            .join(Organisation, Organisation.id == Contract.supplier_org_id)
            .join(CompetitorGroup, CompetitorGroup.id == Organisation.competitor_group_id)
            .join(buyer, buyer.c.id == Contract.buyer_org_id)
            .join(ContractTheme, ContractTheme.ocid == Contract.ocid)
            .join(Theme, Theme.id == ContractTheme.theme_id)
            .where(*conds, *comp_conds, defence_buyer)
            .group_by(CompetitorGroup.slug, Theme.slug, Theme.label)
        ).all()
        theme_agg: dict[str, dict[str, Any]] = {}
        for r in theme_rows:
            if float(r.value) <= 0 or r.cslug not in comp_agg:
                continue
            edges.append(
                NetworkEdge(
                    source=f"c:{r.cslug}", target=f"t:{r.tslug}",
                    value=float(r.value), contract_count=int(r.n),
                )
            )
            t = theme_agg.setdefault(r.tslug, {"label": r.tlabel, "value": 0.0, "n": 0})
            t["value"] += float(r.value)
            t["n"] += int(r.n)
        nodes += [
            NetworkNode(
                id=f"t:{slug}", label=t["label"], kind="theme",
                category=None, slug=slug, value=t["value"], contract_count=t["n"],
            )
            for slug, t in theme_agg.items()
        ]

    return NetworkGraph(
        basis="addressable" if addressable_only else "all-defence",
        nodes=nodes,
        edges=edges,
    )


@router.get("/network/contracts", response_model=NetworkContracts)
def get_network_contracts(
    f: CommonFilters = Depends(common_filters),
    immediate_only: bool = Query(True),
    firm: str | None = Query(None, description="Competitor group slug to drill into"),
    branch: str | None = Query(None, description="Defence branch (buyer_division) to drill into"),
    limit: int = Query(500, ge=1, le=2000),
    session: Session = Depends(get_db),
) -> NetworkContracts:
    """The exact contracts behind the network — same scope as ``/network``."""
    conds = contract_conditions(f)
    comp_conds = [CompetitorGroup.slug != "other"]
    if immediate_only:
        comp_conds = [*comp_conds, CompetitorGroup.category != "defence_prime"]

    supplier = Organisation.__table__.alias("supplier_org")
    buyer = Organisation.__table__.alias("buyer_org")
    defence_buyer = or_(
        buyer.c.name_normalised.in_(list(DEFENCE_BUYER_NORMALISED)),
        buyer.c.name_normalised.like("%defence%"),
    )
    where = [*conds, *comp_conds, defence_buyer]
    if firm:
        where.append(CompetitorGroup.slug == firm)
    if branch:
        where.append(func.coalesce(Contract.buyer_division, buyer.c.name) == branch)

    def base():
        return (
            select(Contract)
            .join(supplier, supplier.c.id == Contract.supplier_org_id)
            .join(CompetitorGroup, CompetitorGroup.id == supplier.c.competitor_group_id)
            .join(buyer, buyer.c.id == Contract.buyer_org_id)
            .where(*where)
        )

    themes_sq = (
        select(func.array_agg(Theme.slug))
        .select_from(ContractTheme)
        .join(Theme, Theme.id == ContractTheme.theme_id)
        .where(ContractTheme.ocid == Contract.ocid)
        .scalar_subquery()
    )
    total = session.execute(base().with_only_columns(func.count())).scalar_one()
    rows = session.execute(
        base()
        .with_only_columns(
            Contract.ocid, Contract.cn_id, Contract.title, Contract.description,
            supplier.c.name.label("supplier_name"),
            CompetitorGroup.slug.label("competitor_slug"),
            CompetitorGroup.label.label("competitor_label"),
            buyer.c.name.label("agency_name"),
            Contract.buyer_division, Contract.buyer_branch,
            Contract.value_amount, Contract.value_currency, Contract.value_per_year,
            Contract.date_published, Contract.date_signed,
            Contract.period_start, Contract.period_end,
            Contract.procurement_method, Contract.unspsc_code, Contract.is_addressable,
            Contract.service_offering, Contract.service_offering_confidence,
            Contract.amendment_count, themes_sq.label("themes"),
        )
        .order_by(Contract.value_amount.desc().nullslast())
        .limit(limit)
    ).all()

    return NetworkContracts(
        total=int(total),
        limit=limit,
        items=[
            NetworkContractRow(
                ocid=r.ocid, cn_id=r.cn_id, title=r.title, description=r.description,
                supplier_name=r.supplier_name, competitor_slug=r.competitor_slug,
                competitor_label=r.competitor_label, agency_name=r.agency_name,
                buyer_division=r.buyer_division, buyer_branch=r.buyer_branch,
                value_amount=float(r.value_amount) if r.value_amount is not None else None,
                value_currency=r.value_currency,
                value_per_year=float(r.value_per_year) if r.value_per_year is not None else None,
                date_published=r.date_published, date_signed=r.date_signed,
                period_start=r.period_start, period_end=r.period_end,
                procurement_method=r.procurement_method, unspsc_code=r.unspsc_code,
                is_addressable=r.is_addressable, service_offering=r.service_offering,
                service_offering_confidence=r.service_offering_confidence,
                amendment_count=r.amendment_count,
                themes=list(r.themes) if r.themes else [],
            )
            for r in rows
        ],
    )


@router.get("/by-agency", response_model=list[AgencyBreakdownRow])
def get_by_agency(
    f: CommonFilters = Depends(common_filters),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_db),
) -> list[AgencyBreakdownRow]:
    """Value and count per buyer (Defence agency)."""
    conds = contract_conditions(f)
    rows = session.execute(
        select(
            Organisation.id,
            Organisation.name,
            func.coalesce(func.sum(Contract.value_amount), 0).label("total_value"),
            func.count().label("contract_count"),
        )
        .select_from(Contract)
        .join(Organisation, Organisation.id == Contract.buyer_org_id)
        .where(*conds)
        .group_by(Organisation.id, Organisation.name)
        .order_by(func.coalesce(func.sum(Contract.value_amount), 0).desc())
        .limit(limit)
    ).all()
    return [
        AgencyBreakdownRow(
            agency_id=r.id,
            agency_name=r.name,
            total_value=float(r.total_value),
            contract_count=int(r.contract_count),
        )
        for r in rows
    ]
