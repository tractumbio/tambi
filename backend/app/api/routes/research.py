"""Pillar III — Deep Research. Commission a brief; get a synthesised report."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.llm.research import run_research
from app.schemas.research import ResearchFindingOut, ResearchReportOut, ResearchRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["research"])


@router.post("", response_model=ResearchReportOut)
def research(req: ResearchRequest) -> ResearchReportOut:
    title = req.title.strip()
    brief = req.brief.strip()
    if not brief:
        raise HTTPException(status_code=400, detail="Research brief must not be empty.")
    if len(brief) > 2000:
        raise HTTPException(status_code=400, detail="Brief is too long (max 2000 chars).")

    try:
        report = run_research(title or "Untitled brief", brief)
    except Exception as exc:  # noqa: BLE001
        logger.exception("research failed")
        raise HTTPException(status_code=500, detail="The research brief could not be completed.") from exc

    return ResearchReportOut(
        title=report.title, brief=report.brief,
        executive_summary=report.executive_summary,
        findings=[ResearchFindingOut(question=f.question, finding=f.finding, sources=f.sources)
                  for f in report.findings],
        recommendation=report.recommendation, sources=report.sources,
    )
