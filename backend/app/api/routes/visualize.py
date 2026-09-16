"""Visual generation — NL prompt → chart spec via text-to-SQL + Claude (Haiku)."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.llm.text_to_sql import SqlGuardError, answer_question

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/visualize", tags=["visualize"])

_PALETTE = ["A100FF", "3B82F6", "10B981", "F59E0B", "EF4444", "8B5CF6", "EC4899", "14B8A6"]

_SYSTEM = """You are a data-visualisation expert. Given a query and its results, produce a chart spec.

Return ONLY valid JSON (no markdown fences) with this exact shape:
{
  "title": "Short descriptive title",
  "chart_type": "bar" | "line" | "area" | "horizontal_bar" | "pie",
  "x_key": "<column name for X axis / category>",
  "series": [{"key": "<numeric column>", "label": "<display name>", "color": "#hex"}],
  "insight": "One sentence key takeaway."
}

Rules:
- x_key and each series.key must be actual column names from the result.
- series.key must refer to a numeric column.
- Use line/area for time-series (columns with year/fy/quarter/month in the name).
- Use horizontal_bar for ranked lists (≤20 items).
- Use bar for small category comparisons.
- Use pie only if there are 2–6 categories and one numeric column.
- Limit series to ≤ 5 for readability.
- Pick colors from: #A100FF #3B82F6 #10B981 #F59E0B #EF4444 #8B5CF6"""


class SeriesSpec(BaseModel):
    key: str
    label: str
    color: str


class VisualizeRequest(BaseModel):
    prompt: str
    refine: str | None = None
    previous_spec: dict | None = None


class VisualizeResponse(BaseModel):
    title: str
    chart_type: str
    x_key: str
    series: list[SeriesSpec]
    data: list[dict[str, Any]]
    insight: str
    sql: str


def _client():
    from app.llm.claude_client import get_anthropic_client
    return get_anthropic_client()


@router.post("", response_model=VisualizeResponse)
def visualize(req: VisualizeRequest) -> VisualizeResponse:
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt must not be empty.")
    if len(prompt) > 600:
        raise HTTPException(status_code=400, detail="Prompt too long (max 600 chars).")

    try:
        ask_result = answer_question(prompt)
    except SqlGuardError as exc:
        raise HTTPException(status_code=422, detail=f"Could not build a safe query: {exc}") from exc
    except Exception as exc:
        logger.exception("visualize: text-to-sql failed")
        raise HTTPException(status_code=500, detail="Could not fetch data for the visual.") from exc

    if not ask_result.rows:
        raise HTTPException(status_code=404, detail="No data found — try rephrasing.")

    refine_ctx = ""
    if req.refine and req.previous_spec:
        refine_ctx = (
            f"\n\nExisting spec to refine:\n{json.dumps(req.previous_spec)}"
            f"\n\nRefinement instruction: {req.refine}"
            "\n\nApply the refinement; keep x_key/series valid against the columns below."
        )

    user_msg = (
        f"Request: {prompt}\n"
        f"SQL: {ask_result.sql}\n"
        f"Columns: {ask_result.columns}\n"
        f"Rows (sample up to 200):\n{json.dumps(ask_result.rows[:200], default=str)}"
        f"{refine_ctx}"
    )

    try:
        resp = _client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=700,
            system=_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        spec = json.loads(raw.strip())
    except Exception as exc:
        logger.exception("visualize: chart spec generation failed")
        raise HTTPException(status_code=500, detail="Chart specification could not be generated.") from exc

    chart_type = spec.get("chart_type", "bar")
    if chart_type not in {"bar", "line", "area", "horizontal_bar", "pie"}:
        chart_type = "bar"

    raw_series = spec.get("series", [])
    series = [
        SeriesSpec(
            key=s["key"],
            label=s.get("label", s["key"]),
            color=s.get("color", f"#{_PALETTE[i % len(_PALETTE)]}"),
        )
        for i, s in enumerate(raw_series)
        if s.get("key")
    ]

    return VisualizeResponse(
        title=spec.get("title", prompt[:60]),
        chart_type=chart_type,
        x_key=spec.get("x_key", ask_result.columns[0] if ask_result.columns else ""),
        series=series,
        data=[dict(r) for r in ask_result.rows],
        insight=spec.get("insight", ""),
        sql=ask_result.sql,
    )
