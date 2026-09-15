"""Request/response models for Pillar II — Ask the Market (text-to-SQL)."""

from __future__ import annotations

from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    question: str
    answer: str
    sql: str
    sources: list[str]
    row_count: int
    columns: list[str]
    rows: list[dict]
