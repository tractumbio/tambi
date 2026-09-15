"""Contract data endpoints (spec Section 9, ``api/contracts``)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import CommonFilters, common_filters, contract_conditions
from app.db.session import get_db
from app.models import CompetitorGroup, Contract, ContractTheme, Organisation, RawRelease, Theme
from app.schemas.contracts import (
    AgencyOption,
    AmendmentRelease,
    CompetitorOption,
    ContractDetail,
    ContractListItem,
    ContractPage,
    DateRange,
    FilterOptions,
    ThemeOption,
    ValueRange,
)

router = APIRouter(tags=["contracts"])

_SORTABLE = {
    "value_amount": Contract.value_amount,
    "date_published": Contract.date_published,
    "period_end": Contract.period_end,
}


def _themes_subquery():
    return (
        select(func.array_agg(Theme.slug))
        .select_from(ContractTheme)
        .join(Theme, Theme.id == ContractTheme.theme_id)
        .where(ContractTheme.ocid == Contract.ocid)
        .scalar_subquery()
    )


@router.get("/contracts", response_model=ContractPage)
def list_contracts(
    f: CommonFilters = Depends(common_filters),
    defence_only: bool = Query(True, description="Restrict to Defence-scoped contracts"),
    sort: str = Query("value_amount", description="value_amount | date_published | period_end"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_db),
) -> ContractPage:
    """Paginated, filterable, sortable contract list."""
    conds = contract_conditions(f, defence_only=defence_only)
    sort_col = _SORTABLE.get(sort, Contract.value_amount)
    ordering = sort_col.desc().nullslast() if order == "desc" else sort_col.asc().nullsfirst()

    supplier = Organisation.__table__.alias("supplier_org")
    buyer = Organisation.__table__.alias("buyer_org")

    total = session.execute(
        select(func.count()).select_from(Contract).where(*conds)
    ).scalar_one()

    rows = session.execute(
        select(
            Contract.ocid,
            Contract.cn_id,
            Contract.title,
            Contract.value_amount,
            Contract.value_currency,
            Contract.date_published,
            Contract.period_end,
            Contract.procurement_method,
            Contract.is_defence,
            buyer.c.name.label("buyer_name"),
            supplier.c.name.label("supplier_name"),
            CompetitorGroup.slug.label("competitor_slug"),
            CompetitorGroup.label.label("competitor_label"),
            _themes_subquery().label("themes"),
        )
        .select_from(Contract)
        .outerjoin(buyer, buyer.c.id == Contract.buyer_org_id)
        .outerjoin(supplier, supplier.c.id == Contract.supplier_org_id)
        .outerjoin(CompetitorGroup, CompetitorGroup.id == supplier.c.competitor_group_id)
        .where(*conds)
        .order_by(ordering)
        .limit(limit)
        .offset(offset)
    ).all()

    items = [
        ContractListItem(
            ocid=r.ocid,
            cn_id=r.cn_id,
            title=r.title,
            buyer_name=r.buyer_name,
            supplier_name=r.supplier_name,
            competitor_slug=r.competitor_slug,
            competitor_label=r.competitor_label,
            value_amount=float(r.value_amount) if r.value_amount is not None else None,
            value_currency=r.value_currency,
            date_published=r.date_published,
            period_end=r.period_end,
            procurement_method=r.procurement_method,
            is_defence=r.is_defence,
            themes=list(r.themes) if r.themes else [],
        )
        for r in rows
    ]
    return ContractPage(items=items, total=int(total), limit=limit, offset=offset)


@router.get("/contracts/{ocid:path}", response_model=ContractDetail)
def get_contract(ocid: str, session: Session = Depends(get_db)) -> ContractDetail:
    """Full contract detail including amendment history from ``raw_releases``."""
    contract = session.get(Contract, ocid)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")

    buyer = session.get(Organisation, contract.buyer_org_id) if contract.buyer_org_id else None
    supplier = (
        session.get(Organisation, contract.supplier_org_id)
        if contract.supplier_org_id
        else None
    )
    group = (
        session.get(CompetitorGroup, supplier.competitor_group_id)
        if supplier and supplier.competitor_group_id
        else None
    )
    theme_slugs = session.execute(
        select(Theme.slug)
        .join(ContractTheme, ContractTheme.theme_id == Theme.id)
        .where(ContractTheme.ocid == ocid)
    ).scalars().all()
    releases = session.execute(
        select(RawRelease)
        .where(RawRelease.ocid == ocid)
        .order_by(RawRelease.release_date.asc().nullsfirst())
    ).scalars().all()

    return ContractDetail(
        ocid=contract.ocid,
        cn_id=contract.cn_id,
        title=contract.title,
        description=contract.description,
        buyer_name=buyer.name if buyer else None,
        supplier_name=supplier.name if supplier else None,
        competitor_slug=group.slug if group else None,
        competitor_label=group.label if group else None,
        value_amount=float(contract.value_amount) if contract.value_amount is not None else None,
        value_currency=contract.value_currency,
        date_published=contract.date_published,
        date_signed=contract.date_signed,
        period_start=contract.period_start,
        period_end=contract.period_end,
        procurement_method=contract.procurement_method,
        unspsc_code=contract.unspsc_code,
        unspsc_title=contract.unspsc_title,
        is_defence=contract.is_defence,
        amendment_count=contract.amendment_count,
        themes=list(theme_slugs),
        releases=[
            AmendmentRelease(
                release_id=rel.release_id,
                release_date=rel.release_date,
                tags=list(rel.tags) if rel.tags else [],
                source_file=rel.source_file,
            )
            for rel in releases
        ],
    )


@router.get("/filters", response_model=FilterOptions)
def get_filters(session: Session = Depends(get_db)) -> FilterOptions:
    """Filter option sets for populating dashboard controls (Defence-scoped)."""
    themes = session.execute(
        select(Theme.slug, Theme.label).order_by(Theme.display_order)
    ).all()
    competitors = session.execute(
        select(CompetitorGroup.slug, CompetitorGroup.label, CompetitorGroup.category).order_by(
            CompetitorGroup.display_order
        )
    ).all()
    agencies = session.execute(
        select(Organisation.id, Organisation.name, func.count().label("n"))
        .join(Contract, Contract.buyer_org_id == Organisation.id)
        .where(Contract.is_defence.is_(True))
        .group_by(Organisation.id, Organisation.name)
        .order_by(func.count().desc())
        .limit(50)
    ).all()
    vmin, vmax = session.execute(
        select(func.min(Contract.value_amount), func.max(Contract.value_amount)).where(
            Contract.is_defence.is_(True)
        )
    ).one()
    dmin, dmax = session.execute(
        select(func.min(Contract.date_published), func.max(Contract.date_published)).where(
            Contract.is_defence.is_(True)
        )
    ).one()

    return FilterOptions(
        themes=[ThemeOption(slug=s, label=lbl) for s, lbl in themes],
        competitors=[
            CompetitorOption(slug=s, label=lbl, category=cat) for s, lbl, cat in competitors
        ],
        agencies=[AgencyOption(id=a.id, name=a.name) for a in agencies],
        value_range=ValueRange(
            min=float(vmin) if vmin is not None else None,
            max=float(vmax) if vmax is not None else None,
        ),
        date_range=DateRange(
            min=dmin.date() if dmin else None, max=dmax.date() if dmax else None
        ),
    )
