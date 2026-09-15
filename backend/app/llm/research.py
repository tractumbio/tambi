"""Pillar III — Deep Research orchestrator.

Turns a free-text research brief into a finished report by decomposing it into concrete
analytical questions, answering each against the contract warehouse via the Pillar II
text-to-SQL engine, then synthesising the findings into an executive report with sources.

Synchronous and multi-step: plan (1 LLM call) → answer N questions (text-to-SQL) →
synthesise (1 LLM call). Latency scales with the number of questions, so it's capped.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.llm.text_to_sql import AskResult, answer_question

_MAX_QUESTIONS = 4


@dataclass
class ResearchFinding:
    question: str
    finding: str
    sources: list[str] = field(default_factory=list)


@dataclass
class ResearchReport:
    title: str
    brief: str
    executive_summary: str
    findings: list[ResearchFinding]
    recommendation: str
    sources: list[str]


def _client():
    import anthropic

    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _text(msg) -> str:
    return msg.content[0].text.strip()


def plan_questions(title: str, brief: str) -> list[str]:
    """Decompose a brief into up to _MAX_QUESTIONS concrete, data-answerable questions."""
    msg = _client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": f"""You are planning a market-intelligence \
investigation of the Australian Defence contract market. The data available is a warehouse \
of awarded Defence contracts (suppliers, buying agencies, values, dates, categories, themes, \
competitor groups such as Accenture / big4 / defence primes).

Research brief:
Title: {title}
Detail: {brief}

Break this into up to {_MAX_QUESTIONS} specific, concrete questions that can each be answered \
by a SQL query over that contract data (about who won what, values, trends over financial \
years, agency concentration, competitor share, expiries, etc.). Avoid questions the data \
can't answer (e.g. future strategy, non-contract news).

Output ONLY a JSON array of question strings, nothing else."""}],
    )
    raw = _text(msg)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return [brief]
    try:
        qs = json.loads(match.group(0))
        return [str(q) for q in qs][:_MAX_QUESTIONS] or [brief]
    except json.JSONDecodeError:
        return [brief]


def synthesise(title: str, brief: str, findings: list[ResearchFinding]) -> tuple[str, str]:
    """Write the executive summary + recommendation from the collected findings."""
    findings_blob = "\n\n".join(
        f"Q: {f.question}\nFinding: {f.finding}" for f in findings
    )
    msg = _client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=900,
        messages=[{"role": "user", "content": f"""You are writing a Defence market-intelligence \
report for Accenture ANZ.

Brief: {title} — {brief}

Findings from the contract data:
{findings_blob}

Write:
1. An executive summary (3–5 sentences) synthesising the findings into a clear market picture.
2. A recommendation (2–4 sentences) on the implication for Accenture — where to focus, what to watch.

Use AUD magnitudes ($1.2B, $340M). Ground every claim in the findings above; do not invent data.

Output ONLY a JSON object, no fences:
{{"executive_summary": "...", "recommendation": "..."}}"""}],
    )
    raw = _text(msg)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group(0))
            return obj.get("executive_summary", ""), obj.get("recommendation", "")
        except json.JSONDecodeError:
            pass
    return raw, ""


def run_research(title: str, brief: str) -> ResearchReport:
    questions = plan_questions(title, brief)

    findings: list[ResearchFinding] = []
    all_sources: list[str] = []
    for q in questions:
        try:
            res: AskResult = answer_question(q)
            findings.append(ResearchFinding(question=q, finding=res.answer, sources=res.sources))
            all_sources.extend(res.sources)
        except Exception:
            findings.append(ResearchFinding(
                question=q, finding="This question could not be answered from the available data.",
                sources=[],
            ))

    exec_summary, recommendation = synthesise(title, brief, findings)

    # de-dupe sources, preserve order
    seen: set[str] = set()
    sources = [s for s in all_sources if not (s in seen or seen.add(s))]

    return ResearchReport(
        title=title, brief=brief, executive_summary=exec_summary,
        findings=findings, recommendation=recommendation, sources=sources,
    )
