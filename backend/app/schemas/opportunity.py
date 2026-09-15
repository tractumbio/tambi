"""Response models for the opportunity-side endpoints (ATMs)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class AtmRow(BaseModel):
    atm_id: str
    title: str | None
    description: str | None
    agency_name: str | None
    atm_type: str | None
    unspsc_code: str | None
    unspsc_title: str | None
    published_date: date | None
    close_date: datetime | None
    days_to_close: int | None
    location_state: str | None
    is_defence: bool
    status: str
    url: str | None


class AtmPage(BaseModel):
    total: int
    limit: int
    items: list[AtmRow]


# ── Capability-match scored response ──────────────────────────────────────────

class CompetitorScore(BaseModel):
    slug: str
    label: str
    category: str
    score: int                      # 0–100
    capability_signal: float        # 0–1  (track-record match, primary)
    unspsc_signal: float            # 0–1
    has_agency_relationship: bool   # tick — prior contract with this buyer (not scored)


class ScoredAtmRow(AtmRow):
    accenture_score: int
    accenture_grade: str           # A/B/C/D
    recommendation: str            # pursue/watch/monitor/pass
    accenture_capability_signal: float
    accenture_unspsc_signal: float
    accenture_has_agency_relationship: bool
    competitor_scores: list[CompetitorScore]  # sorted score desc, all non-other
    threat_level: str              # high/medium/low
    top_threat_slug: str | None


class ScoredAtmPage(BaseModel):
    total: int
    limit: int
    scoring_mode: str              # "embedding" (Voyage) | "tfidf" (fallback)
    items: list[ScoredAtmRow]


# ── AI analysis response ──────────────────────────────────────────────────────

class AiCompetitorThreat(BaseModel):
    slug: str
    label: str
    score: int
    reason: str


class AiScoreResult(BaseModel):
    atm_id: str
    accenture_score: int
    grade: str
    recommendation: str
    rationale: str
    win_factors: list[str]
    capability_gaps: list[str]
    competitor_threats: list[AiCompetitorThreat]
