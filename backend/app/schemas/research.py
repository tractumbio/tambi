"""Request/response models for Pillar III — Deep Research."""

from __future__ import annotations

from pydantic import BaseModel


class ResearchRequest(BaseModel):
    title: str
    brief: str


class ResearchFindingOut(BaseModel):
    question: str
    finding: str
    sources: list[str]


class ResearchReportOut(BaseModel):
    title: str
    brief: str
    executive_summary: str
    findings: list[ResearchFindingOut]
    recommendation: str
    sources: list[str]
