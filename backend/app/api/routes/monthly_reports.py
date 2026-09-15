"""Pillar III — monthly market-intelligence reports (generate, list, read)."""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.intelligence.monthly_report import DEFAULT_STRUCTURE, default_period, generate_report
from app.models import MonthlyReport
from app.schemas.monthly_report import (
    GenerateReportRequest,
    MonthlyReportOut,
    MonthlyReportSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monthly-reports", tags=["monthly-reports"])

_MODELS = {"claude-haiku-4-5-20251001", "claude-sonnet-5", "claude-opus-5"}
_EFFORTS = {"low", "standard", "deep"}


def _summary(r: MonthlyReport) -> MonthlyReportSummary:
    return MonthlyReportSummary(
        id=r.id, period_start=r.period_start, period_end=r.period_end,
        generated_at=r.generated_at, status=r.status, model=r.model, effort=r.effort,
        title=r.title, contract_source_count=r.contract_source_count,
        news_source_count=r.news_source_count,
    )


def _full(r: MonthlyReport) -> MonthlyReportOut:
    return MonthlyReportOut(
        **_summary(r).model_dump(),
        executive_summary=r.executive_summary, payload=r.payload,
    )


@router.get("", response_model=list[MonthlyReportSummary])
def list_reports(
    limit: int = Query(50, ge=1, le=200), session: Session = Depends(get_db)
) -> list[MonthlyReportSummary]:
    rows = session.execute(
        select(MonthlyReport).order_by(MonthlyReport.period_start.desc(),
                                       MonthlyReport.generated_at.desc()).limit(limit)
    ).scalars().all()
    return [_summary(r) for r in rows]


@router.get("/default-structure")
def get_default_structure() -> dict:
    """The editable report outline shown as the textbox default in the UI."""
    return {"structure": DEFAULT_STRUCTURE}


@router.get("/coverage")
def get_coverage(
    start: date | None = Query(None), end: date | None = Query(None),
    session: Session = Depends(get_db),
) -> dict:
    """Data-availability summary for a period — contracts, opportunities, media, releases."""
    from app.intelligence.facts import build_coverage

    if not (start and end):
        start, end = default_period()
    if end <= start:
        raise HTTPException(status_code=400, detail="end must be after start")
    return build_coverage(session, start, end)


@router.get("/sources")
def get_sources(session: Session = Depends(get_db)) -> dict:
    """What feeds a report — deterministic data + the reputable news allowlist + corpus size."""
    from app.intelligence.harvest_news import get_allowed_domains
    from app.models import KnowledgeItem

    corpus = session.execute(
        select(func.count()).select_from(KnowledgeItem)
    ).scalar_one()
    return {
        "data_sources": [
            "New contract awards (AusTender OCDS, first-release dates)",
            "Contract amendments (raw release history)",
            "Expiries & recompetes (period_end roll-off)",
            "Competitor momentum (rolling 12-month value)",
            "Spend & theme trends (deterministic SQL aggregates)",
        ],
        "news_domains": get_allowed_domains(session),
        "corpus_size": int(corpus),
    }


# ── editable reputable-domain allowlist ──────────────────────────────────────

class DomainIn(BaseModel):
    domain: str
    label: str | None = None


def _normalise_domain(raw: str) -> str:
    from urllib.parse import urlparse

    d = raw.strip().lower()
    if "//" in d:
        d = urlparse(d).hostname or d
    d = d.lstrip(".")
    if d.startswith("www."):
        d = d[4:]
    return d.rstrip("/")


@router.get("/domains")
def list_domains(session: Session = Depends(get_db)) -> list[dict]:
    from app.intelligence.harvest_news import get_allowed_domains
    from app.models import NewsDomain

    get_allowed_domains(session)  # ensure seeded
    rows = session.execute(select(NewsDomain).order_by(NewsDomain.domain)).scalars().all()
    return [{"domain": r.domain, "label": r.label, "enabled": r.enabled} for r in rows]


@router.post("/domains")
def add_domain(body: DomainIn, session: Session = Depends(get_db)) -> dict:
    from app.models import NewsDomain

    domain = _normalise_domain(body.domain)
    if not domain or "." not in domain or " " in domain:
        raise HTTPException(status_code=400, detail="Enter a valid domain, e.g. example.com")
    existing = session.execute(select(NewsDomain).where(NewsDomain.domain == domain)).scalar_one_or_none()
    if existing:
        existing.enabled = True
    else:
        session.add(NewsDomain(domain=domain, label=body.label, enabled=True))
    session.commit()
    return {"domain": domain, "enabled": True}


@router.delete("/domains/{domain}")
def remove_domain(domain: str, session: Session = Depends(get_db)) -> dict:
    from app.models import NewsDomain

    row = session.execute(
        select(NewsDomain).where(NewsDomain.domain == _normalise_domain(domain))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Domain not found.")
    session.delete(row)
    session.commit()
    return {"removed": domain}


@router.post("/harvest")
def trigger_harvest(session: Session = Depends(get_db), effort: str = Query("standard"),
                    model: str = Query("claude-haiku-4-5-20251001")) -> dict:
    """Run a news harvest now (accumulate the knowledge base from the allowlist)."""
    from app.intelligence.harvest_news import run_harvest

    try:
        r = run_harvest(session, model=model, effort=effort if effort in _EFFORTS else "standard")
    except Exception as exc:  # noqa: BLE001
        logger.exception("harvest failed")
        raise HTTPException(status_code=500, detail="Harvest failed — check the domain allowlist.") from exc
    return {"fetched": r.fetched, "inserted": r.inserted, "updated": r.updated}


@router.get("/latest", response_model=MonthlyReportOut)
def latest_report(session: Session = Depends(get_db)) -> MonthlyReportOut:
    r = session.execute(
        select(MonthlyReport).order_by(MonthlyReport.period_start.desc(),
                                       MonthlyReport.generated_at.desc()).limit(1)
    ).scalar_one_or_none()
    if r is None:
        raise HTTPException(status_code=404, detail="No reports generated yet.")
    return _full(r)


@router.get("/{report_id}", response_model=MonthlyReportOut)
def get_report(report_id: int, session: Session = Depends(get_db)) -> MonthlyReportOut:
    r = session.get(MonthlyReport, report_id)
    if r is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found.")
    return _full(r)


@router.post("/generate", response_model=MonthlyReportOut)
def generate(req: GenerateReportRequest, session: Session = Depends(get_db)) -> MonthlyReportOut:
    # Resolve the period window.
    if req.month:
        try:
            year, month = (int(x) for x in req.month.split("-"))
            start = date(year, month, 1)
            end = date(year + (month // 12), (month % 12) + 1, 1)
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=400, detail="month must be YYYY-MM") from exc
    elif req.period_start and req.period_end:
        start, end = req.period_start, req.period_end
    else:
        start, end = default_period()

    if end <= start:
        raise HTTPException(status_code=400, detail="period_end must be after period_start")

    model = req.model if req.model in _MODELS else "claude-sonnet-5"
    effort = req.effort if req.effort in _EFFORTS else "standard"

    try:
        report = generate_report(session, start, end, model=model, effort=effort,
                                 structure=req.structure)
    except Exception as exc:  # noqa: BLE001
        logger.exception("monthly report generation failed")
        raise HTTPException(status_code=500, detail="Report generation failed.") from exc

    return _full(report)
