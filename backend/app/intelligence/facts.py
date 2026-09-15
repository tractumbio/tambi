"""Deterministic fact builder for the monthly market-intelligence report.

Every figure in the report is computed here from SQL — the LLM never invents a number
(BUILD_SPEC §12.7: "numbers come from the database, never from the model"). Returns a
plain jsonable dict that is both stored on the report and handed to the synthesiser as
the sole source of quantitative truth.

Change-detection basis (publication-accurate, via the append-only ``raw_releases`` feed):
  * NEW awards      — ocids whose FIRST release date falls in the window.
  * AMENDMENTS      — ocids whose first release predates the window but have a release in it.
  * EXPIRIES        — contracts whose ``period_end`` falls in the window (recompete roll-off).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import ColumnElement, Numeric, case, cast, func, select
from sqlalchemy.orm import Session

from app.api.deps import ACCENTURE_SLUG
from app.models import (
    CompetitorGroup,
    Contract,
    ContractTheme,
    Organisation,
    RawRelease,
    Theme,
)

_MONEY = Numeric(18, 2)
_NOTABLE_LIMIT = 10


def _dt(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


def _accenture_supplier_ids():
    return (
        select(Organisation.id)
        .join(CompetitorGroup, CompetitorGroup.id == Organisation.competitor_group_id)
        .where(CompetitorGroup.slug == ACCENTURE_SLUG)
    )


# ── movement ocid sets (via raw_releases) ─────────────────────────────────────

def _first_release_sq():
    return (
        select(RawRelease.ocid, func.min(RawRelease.release_date).label("first_date"))
        .group_by(RawRelease.ocid)
        .subquery()
    )


def _new_award_ocids(start: date, end: date):
    fr = _first_release_sq()
    return select(fr.c.ocid).where(fr.c.first_date >= _dt(start), fr.c.first_date < _dt(end))


def _amended_ocids(start: date, end: date):
    fr = _first_release_sq()
    in_window = (
        select(RawRelease.ocid)
        .where(RawRelease.release_date >= _dt(start), RawRelease.release_date < _dt(end))
        .distinct()
    )
    return select(fr.c.ocid).where(fr.c.first_date < _dt(start), fr.c.ocid.in_(in_window))


# ── aggregation helpers ───────────────────────────────────────────────────────

def _totals(session: Session, cond: ColumnElement[bool]) -> tuple[float, int]:
    v, c = session.execute(
        select(func.coalesce(func.sum(Contract.value_amount), 0), func.count())
        .where(Contract.is_defence.is_(True), cond)
    ).one()
    return float(v), int(c)


def _by_competitor(session: Session, cond: ColumnElement[bool]) -> list[dict]:
    slug = func.coalesce(CompetitorGroup.slug, "other")
    label = func.coalesce(CompetitorGroup.label, "Other")
    cat = func.coalesce(CompetitorGroup.category, "other")
    rows = session.execute(
        select(slug, label, cat, func.coalesce(func.sum(Contract.value_amount), 0), func.count())
        .select_from(Contract)
        .outerjoin(Organisation, Organisation.id == Contract.supplier_org_id)
        .outerjoin(CompetitorGroup, CompetitorGroup.id == Organisation.competitor_group_id)
        .where(Contract.is_defence.is_(True), cond)
        .group_by(slug, label, cat)
        .order_by(func.coalesce(func.sum(Contract.value_amount), 0).desc())
    ).all()
    return [
        {"slug": r[0], "label": r[1], "category": r[2], "value": float(r[3]), "count": int(r[4])}
        for r in rows
    ]


def _notable(session: Session, cond: ColumnElement[bool], limit: int = _NOTABLE_LIMIT) -> list[dict]:
    supplier = Organisation.__table__.alias("supplier_org")
    buyer = Organisation.__table__.alias("buyer_org")
    rows = session.execute(
        select(
            Contract.cn_id, Contract.title, Contract.value_amount,
            Contract.date_published, Contract.period_end,
            buyer.c.name.label("agency"), supplier.c.name.label("supplier"),
            CompetitorGroup.slug.label("cslug"), CompetitorGroup.label.label("clabel"),
        )
        .select_from(Contract)
        .outerjoin(buyer, buyer.c.id == Contract.buyer_org_id)
        .outerjoin(supplier, supplier.c.id == Contract.supplier_org_id)
        .outerjoin(CompetitorGroup, CompetitorGroup.id == supplier.c.competitor_group_id)
        .where(Contract.is_defence.is_(True), cond)
        .order_by(Contract.value_amount.desc().nullslast())
        .limit(limit)
    ).all()
    out = []
    for r in rows:
        out.append({
            "cn_id": r.cn_id,
            "title": r.title,
            "value": float(r.value_amount) if r.value_amount is not None else None,
            "agency": r.agency,
            "supplier": r.supplier,
            "competitor_slug": r.cslug,
            "competitor_label": r.clabel or "Other",
            "date_published": r.date_published.date().isoformat() if r.date_published else None,
            "period_end": r.period_end.isoformat() if r.period_end else None,
        })
    return out


def _movement(session: Session, cond: ColumnElement[bool]) -> dict:
    total_value, total_count = _totals(session, cond)
    return {
        "total_value": total_value,
        "total_count": total_count,
        "by_competitor": _by_competitor(session, cond),
        "notable": _notable(session, cond),
    }


# ── main entry point ──────────────────────────────────────────────────────────

def build_facts(session: Session, start: date, end: date) -> dict:
    """Compute all deterministic figures for the report window ``[start, end)``."""
    new_cond = Contract.ocid.in_(_new_award_ocids(start, end))
    amend_cond = Contract.ocid.in_(_amended_ocids(start, end))
    expiry_cond = (Contract.period_end >= start) & (Contract.period_end < end)

    new_awards = _movement(session, new_cond)
    amendments = _movement(session, amend_cond)
    expiries = _movement(session, expiry_cond)

    # Spend: the window's newly-awarded value vs the previous equal-length window.
    span = end - start
    prev_start, prev_end = start - span, start
    prev_value, prev_count = _totals(session, Contract.ocid.in_(_new_award_ocids(prev_start, prev_end)))
    delta_pct = (
        round((new_awards["total_value"] - prev_value) / prev_value * 100, 1)
        if prev_value > 0 else None
    )

    # Accenture's slice of the window's new awards.
    acc_value, acc_count = _totals(
        session, new_cond & Contract.supplier_org_id.in_(_accenture_supplier_ids())
    )
    acc_share = round(acc_value / new_awards["total_value"], 4) if new_awards["total_value"] else 0.0

    # Rolling 12-month competitor momentum anchored at the window end.
    momentum = _momentum(session, end)

    # Theme mix of the window's new awards.
    by_theme = _by_theme(session, new_cond)

    # Collect all cited CN ids for provenance.
    cn_ids: list[str] = []
    for section in (new_awards, amendments, expiries):
        for item in section["notable"]:
            if item["cn_id"]:
                cn_ids.append(item["cn_id"])
    seen: set[str] = set()
    cn_ids = [c for c in cn_ids if not (c in seen or seen.add(c))]

    # Label: a clean calendar month shows "August 2026"; any other window shows a range.
    is_cal_month = start.day == 1 and end == (
        date(start.year + (start.month // 12), (start.month % 12) + 1, 1)
    )
    last = end - timedelta(days=1)
    label = start.strftime("%B %Y") if is_cal_month else (
        f"{start.strftime('%d %b')} – {last.strftime('%d %b %Y')}"
    )

    return {
        "window": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "label": label,
            "days": span.days,
        },
        "spend": {
            "new_award_value": new_awards["total_value"],
            "new_award_count": new_awards["total_count"],
            "prev_window_value": prev_value,
            "prev_window_count": prev_count,
            "delta_pct": delta_pct,
            "accenture_value": acc_value,
            "accenture_count": acc_count,
            "accenture_share": acc_share,
        },
        "new_awards": new_awards,
        "amendments": amendments,
        "expiries": expiries,
        "competitor_momentum": momentum,
        "by_theme": by_theme,
        "contract_source_cn_ids": cn_ids,
    }


def build_coverage(session: Session, start: date, end: date) -> dict:
    """Lightweight data-availability summary for a period — what feeds a report.

    Counts across the four source types the report draws on, so the user can see the
    shape of the window before generating.
    """
    from app.models import Atm, KnowledgeItem

    new_cond = Contract.ocid.in_(_new_award_ocids(start, end))
    amend_cond = Contract.ocid.in_(_amended_ocids(start, end))
    expiry_cond = (Contract.period_end >= start) & (Contract.period_end < end)

    new_value, new_n = _totals(session, new_cond)
    _, amend_n = _totals(session, amend_cond)
    exp_value, exp_n = _totals(session, expiry_cond)

    # Opportunities (ATMs).
    open_atms = int(session.execute(
        select(func.count()).select_from(Atm)
        .where(Atm.is_defence.is_(True), Atm.status == "open")
    ).scalar_one())
    closing = int(session.execute(
        select(func.count()).select_from(Atm)
        .where(Atm.is_defence.is_(True), Atm.close_date >= _dt(start), Atm.close_date < _dt(end))
    ).scalar_one())

    # Media / knowledge base (published in window).
    pub_in = (KnowledgeItem.published_date >= start) & (KnowledgeItem.published_date < end)
    disc_in = (KnowledgeItem.published_date.is_(None)
               & (KnowledgeItem.first_seen_at >= _dt(start))
               & (KnowledgeItem.first_seen_at < _dt(end)))
    media_rows = session.execute(
        select(KnowledgeItem.category, func.count()).where(pub_in | disc_in)
        .group_by(KnowledgeItem.category)
    ).all()
    by_cat = {c: int(n) for c, n in media_rows}

    return {
        "period": {"start": start.isoformat(), "end": end.isoformat(), "days": (end - start).days},
        "contracts": {
            "new_awards": new_n, "new_value": new_value,
            "amendments": amend_n, "expiries": exp_n, "expiry_value": exp_value,
        },
        "opportunities": {"open_atms": open_atms, "closing_in_period": closing},
        "media": {"total": sum(by_cat.values()), "by_category": by_cat},
        "defence_releases": by_cat.get("government", 0),
    }


def _momentum(session: Session, anchor: date) -> list[dict]:
    start_12 = _dt(anchor) - timedelta(days=365)
    start_24 = start_12 - timedelta(days=365)
    v12 = case((Contract.date_published >= start_12, Contract.value_amount), else_=0)
    c12 = case((Contract.date_published >= start_12, 1), else_=0)
    vprev = case(
        ((Contract.date_published >= start_24) & (Contract.date_published < start_12),
         Contract.value_amount),
        else_=0,
    )
    rows = session.execute(
        select(
            CompetitorGroup.slug, CompetitorGroup.label, CompetitorGroup.category,
            func.coalesce(func.sum(cast(v12, _MONEY)), 0).label("v12"),
            func.coalesce(func.sum(c12), 0).label("c12"),
            func.coalesce(func.sum(cast(vprev, _MONEY)), 0).label("vprev"),
        )
        .select_from(Contract)
        .join(Organisation, Organisation.id == Contract.supplier_org_id)
        .join(CompetitorGroup, CompetitorGroup.id == Organisation.competitor_group_id)
        .where(Contract.is_defence.is_(True), Contract.date_published >= start_24,
               CompetitorGroup.slug != "other")
        .group_by(CompetitorGroup.slug, CompetitorGroup.label, CompetitorGroup.category,
                  CompetitorGroup.display_order)
        .order_by(func.coalesce(func.sum(cast(v12, _MONEY)), 0).desc())
    ).all()
    out = []
    for r in rows:
        v12v, vp = float(r.v12), float(r.vprev)
        trend = "up" if v12v > vp * 1.05 else "down" if v12v < vp * 0.95 else "flat"
        out.append({
            "slug": r.slug, "label": r.label, "category": r.category,
            "value_12m": v12v, "count_12m": int(r.c12), "value_prev_12m": vp, "trend": trend,
        })
    return out


def _by_theme(session: Session, cond: ColumnElement[bool]) -> list[dict]:
    rows = session.execute(
        select(
            Theme.slug, Theme.label,
            func.coalesce(func.sum(Contract.value_amount), 0).label("value"),
            func.count(func.distinct(Contract.ocid)).label("n"),
        )
        .select_from(Contract)
        .join(ContractTheme, ContractTheme.ocid == Contract.ocid)
        .join(Theme, Theme.id == ContractTheme.theme_id)
        .where(Contract.is_defence.is_(True), cond)
        .group_by(Theme.slug, Theme.label, Theme.display_order)
        .order_by(func.coalesce(func.sum(Contract.value_amount), 0).desc())
    ).all()
    return [
        {"slug": r.slug, "label": r.label, "value": float(r.value), "count": int(r.n)}
        for r in rows
    ]
