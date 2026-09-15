"""Opportunity-side endpoints — Approaches to Market (ATMs)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Atm
from app.processing.capability import (
    atm_embedding,
    atm_vector,
    get_fingerprints,
    grade,
    recommend,
    score_atm,
    scoring_mode,
    threat_level,
)
from app.schemas.opportunity import (
    AiScoreResult,
    AtmPage,
    AtmRow,
    CompetitorScore,
    ScoredAtmPage,
    ScoredAtmRow,
)

router = APIRouter(prefix="/opportunities", tags=["opportunities"])

_ATM_URL = "https://www.tenders.gov.au/Atm/Show/{uuid}"


def _atm_row(a: Atm, today: datetime) -> AtmRow:
    return AtmRow(
        atm_id=a.atm_id, title=a.title, description=a.description,
        agency_name=a.agency_name, atm_type=a.atm_type,
        unspsc_code=a.unspsc_code, unspsc_title=a.unspsc_title,
        published_date=a.published_date, close_date=a.close_date,
        days_to_close=(a.close_date - today).days if a.close_date else None,
        location_state=a.location_state, is_defence=a.is_defence, status=a.status,
        url=_ATM_URL.format(uuid=a.atm_uuid) if a.atm_uuid else None,
    )


@router.get("/atms", response_model=AtmPage)
def list_atms(
    defence_only: bool = Query(True, description="Restrict to Defence ATMs"),
    status: str = Query("open", pattern="^(open|closed|all)$"),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_db),
) -> AtmPage:
    """Approaches to Market, soonest close first — the live opportunity pipeline."""
    conds = []
    if defence_only:
        conds.append(Atm.is_defence.is_(True))
    if status != "all":
        conds.append(Atm.status == status)

    total = session.execute(select(func.count()).select_from(Atm).where(*conds)).scalar_one()
    rows = session.execute(
        select(Atm).where(*conds).order_by(Atm.close_date.asc().nullslast()).limit(limit)
    ).scalars().all()

    today = datetime.now(UTC)
    return AtmPage(
        total=int(total),
        limit=limit,
        items=[_atm_row(a, today) for a in rows],
    )


@router.get("/atms/scored", response_model=ScoredAtmPage)
def list_scored_atms(
    defence_only: bool = Query(True),
    status: str = Query("open", pattern="^(open|closed|all)$"),
    limit: int = Query(200, ge=1, le=500),
    session: Session = Depends(get_db),
) -> ScoredAtmPage:
    """ATMs enriched with per-competitor capability-match scores.

    Accenture's score and all non-other competitor scores are returned; sorted by
    Accenture score descending so the most-addressable opportunities surface first.
    Fingerprints are cached for 5 min; first call may be ~200 ms, subsequent calls
    are sub-millisecond.
    """
    conds = []
    if defence_only:
        conds.append(Atm.is_defence.is_(True))
    if status != "all":
        conds.append(Atm.status == status)

    total = session.execute(select(func.count()).select_from(Atm).where(*conds)).scalar_one()
    atms = session.execute(
        select(Atm).where(*conds).order_by(Atm.close_date.asc().nullslast()).limit(limit)
    ).scalars().all()

    fps = get_fingerprints(session)
    today = datetime.now(UTC)

    scored: list[ScoredAtmRow] = []
    for a in atms:
        base = _atm_row(a, today)
        # Vectorise this ATM once, reuse across every firm.
        vec = atm_vector(a.title, a.description)
        emb = atm_embedding(a.title, a.description)

        comp_scores: list[CompetitorScore] = []
        for slug, fp in fps.items():
            if slug == "accenture":
                continue
            sig = score_atm(a.unspsc_code, a.agency_name, fp, vec, atm_embedding=emb)
            comp_scores.append(CompetitorScore(
                slug=slug, label=fp.label, category=fp.category, score=sig.score,
                capability_signal=sig.capability, unspsc_signal=sig.unspsc,
                has_agency_relationship=sig.has_agency_relationship,
            ))
        comp_scores.sort(key=lambda c: c.score, reverse=True)

        acc_fp = fps.get("accenture")
        if acc_fp:
            acc_sig = score_atm(a.unspsc_code, a.agency_name, acc_fp, vec, atm_embedding=emb)
            acc_score = acc_sig.score
            acc_cap, acc_unspsc = acc_sig.capability, acc_sig.unspsc
            acc_agency = acc_sig.has_agency_relationship
        else:
            acc_score, acc_cap, acc_unspsc, acc_agency = 0, 0.0, 0.0, False

        max_comp = comp_scores[0].score if comp_scores else 0
        top_threat = comp_scores[0].slug if comp_scores and comp_scores[0].score > 0 else None

        scored.append(ScoredAtmRow(
            **base.model_dump(),
            accenture_score=acc_score,
            accenture_grade=grade(acc_score),
            recommendation=recommend(acc_score),
            accenture_capability_signal=acc_cap,
            accenture_unspsc_signal=acc_unspsc,
            accenture_has_agency_relationship=acc_agency,
            competitor_scores=comp_scores,
            threat_level=threat_level(max_comp),
            top_threat_slug=top_threat,
        ))

    scored.sort(key=lambda r: r.accenture_score, reverse=True)
    return ScoredAtmPage(
        total=int(total), limit=limit, scoring_mode=scoring_mode(fps), items=scored,
    )


@router.post("/atms/{atm_id}/ai-score", response_model=AiScoreResult)
def ai_score_atm(
    atm_id: str,
    session: Session = Depends(get_db),
) -> AiScoreResult:
    """LLM-powered deep analysis of a single ATM against Accenture's capability profile.

    Calls Claude Haiku with a structured prompt; returns a richer score, rationale,
    win factors, capability gaps, and top competitor threats. Latency ~2–4 s.
    """
    from app.llm.claude_client import analyse_atm

    atm = session.execute(select(Atm).where(Atm.atm_id == atm_id)).scalar_one_or_none()
    if atm is None:
        raise HTTPException(status_code=404, detail=f"ATM {atm_id!r} not found")

    # Build Accenture's capability profile for the prompt
    fps = get_fingerprints(session)
    acc_fp = fps.get("accenture")
    acc_count = acc_fp.contract_count if acc_fp else 0

    # Top UNSPSC categories with labels from actual contracts
    unspsc_rows = session.execute(text("""
        SELECT c.unspsc_code, c.unspsc_title, COUNT(*) AS cnt
        FROM contracts c
        JOIN organisations o_s ON c.supplier_org_id = o_s.id
        JOIN competitor_groups cg ON o_s.competitor_group_id = cg.id
        WHERE cg.slug = 'accenture' AND c.is_defence = TRUE
          AND c.unspsc_code IS NOT NULL
        GROUP BY c.unspsc_code, c.unspsc_title
        ORDER BY cnt DESC LIMIT 6
    """)).fetchall()
    unspsc_profile = [{"code": r.unspsc_code, "title": r.unspsc_title, "count": r.cnt}
                      for r in unspsc_rows]

    # Top agencies
    agency_rows = session.execute(text("""
        SELECT o_b.name, COUNT(*) AS cnt
        FROM contracts c
        JOIN organisations o_s ON c.supplier_org_id = o_s.id
        JOIN competitor_groups cg ON o_s.competitor_group_id = cg.id
        JOIN organisations o_b ON c.buyer_org_id = o_b.id
        WHERE cg.slug = 'accenture' AND c.is_defence = TRUE
        GROUP BY o_b.name ORDER BY cnt DESC LIMIT 5
    """)).fetchall()
    agency_profile = [{"name": r.name, "count": r.cnt} for r in agency_rows]

    # Service offerings
    offering_rows = session.execute(text("""
        SELECT service_offering, COUNT(*) AS cnt
        FROM contracts c
        JOIN organisations o_s ON c.supplier_org_id = o_s.id
        JOIN competitor_groups cg ON o_s.competitor_group_id = cg.id
        WHERE cg.slug = 'accenture' AND c.is_defence = TRUE
          AND c.service_offering IS NOT NULL
        GROUP BY service_offering ORDER BY cnt DESC
    """)).fetchall()
    offering_profile = [{"offering": r.service_offering, "count": r.cnt} for r in offering_rows]

    today = datetime.now(UTC)
    days = (atm.close_date - today).days if atm.close_date else None

    raw = analyse_atm(
        atm_title=atm.title,
        atm_description=atm.description,
        atm_agency=atm.agency_name,
        atm_unspsc_title=atm.unspsc_title,
        atm_unspsc_code=atm.unspsc_code,
        atm_type=atm.atm_type,
        days_to_close=days,
        accenture_unspsc_profile=unspsc_profile,
        accenture_agency_profile=agency_profile,
        accenture_offering_profile=offering_profile,
        accenture_contract_count=acc_count,
    )

    threats = [
        {"slug": t["slug"], "label": t["label"], "score": t["score"], "reason": t["reason"]}
        for t in raw.get("competitor_threats", [])[:5]
    ]
    return AiScoreResult(
        atm_id=atm_id,
        accenture_score=raw.get("accenture_score", 0),
        grade=raw.get("grade", "D"),
        recommendation=raw.get("recommendation", "pass"),
        rationale=raw.get("rationale", ""),
        win_factors=raw.get("win_factors", []),
        capability_gaps=raw.get("capability_gaps", []),
        competitor_threats=threats,
    )
