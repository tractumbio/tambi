"""Monthly market-intelligence report orchestrator (Pillar III).

Fuses three inputs into one stored, standardized report:
  1. deterministic contract facts (``facts.build_facts`` — numbers from SQL, never the model),
  2. stored, cited news for the window from the knowledge base (``news.news_for_window``), and
  3. how much the knowledge base changed since last period (``news.knowledge_delta``).

The LLM only *narrates* from these structured inputs (executive summary, section prose,
implications) — every figure and source is pre-computed. Reproducible: regenerating a
period reads the same stored facts + knowledge items.

CLI:  python -m app.intelligence.monthly_report [--month YYYY-MM | --from D --to D]
                                                 [--model ...] [--effort low|standard|deep]
"""

from __future__ import annotations

import argparse
import json
import re
from calendar import monthrange
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.intelligence.facts import build_facts
from app.intelligence.news import knowledge_delta, news_for_window
from app.models import MonthlyReport

_MODELS = {"claude-haiku-4-5-20251001", "claude-sonnet-5", "claude-opus-5"}
_EFFORT_TOKENS = {"low": 1600, "standard": 2600, "deep": 3600}

DEFAULT_STRUCTURE = """\
1. Executive Summary — bottom line up front: 3-5 key takeaways and their implication for Accenture.
2. Contract Movements — new awards, amendments, and expiries/recompetes, focused on competitors.
3. Expenditure & Market Trends — spend trend vs prior period, competitor momentum, positioning, notable deals.
4. Market Intelligence — significant competitor, government/policy and macro news (with sources), and what changed since last report.
5. Implications & Watch-list for Accenture."""


def default_period(today: date | None = None) -> tuple[date, date]:
    """Rolling last 30 days as [start, end)."""
    from datetime import timedelta

    today = today or datetime.now(UTC).date()
    end = today + timedelta(days=1)  # inclusive of today
    start = end - timedelta(days=30)
    return start, end


def _client():
    from app.llm.claude_client import get_anthropic_client
    return get_anthropic_client()


def _m(v: float) -> str:
    a = abs(v)
    if a >= 1e9:
        return f"${v / 1e9:.1f}B"
    if a >= 1e6:
        return f"${v / 1e6:.1f}M"
    if a >= 1e3:
        return f"${v / 1e3:.0f}k"
    return f"${v:.0f}"


def _compact_facts(facts: dict) -> dict:
    """Trim the deterministic facts to a prompt-sized structured summary."""
    def comp(section: str, n_notable: int = 6) -> dict:
        s = facts[section]
        return {
            "total_value": s["total_value"],
            "total_count": s["total_count"],
            "by_competitor": s["by_competitor"][:8],
            "notable": [
                {"cn_id": i["cn_id"], "title": i["title"], "value": i["value"],
                 "agency": i["agency"], "competitor": i["competitor_label"]}
                for i in s["notable"][:n_notable]
            ],
        }

    return {
        "window": facts["window"],
        "spend": facts["spend"],
        "new_awards": comp("new_awards"),
        "amendments": comp("amendments"),
        "expiries": comp("expiries"),
        "competitor_momentum": facts["competitor_momentum"][:8],
        "by_theme": facts["by_theme"][:8],
    }


def synthesise(model: str, effort: str, facts: dict, news: list[dict], delta: dict,
               structure: str) -> dict:
    max_tokens = _EFFORT_TOKENS.get(effort, 2600)
    payload = {
        "facts": _compact_facts(facts),
        "news": [
            {"headline": n["headline"], "summary": n["summary"], "url": n["url"],
             "category": n["category"], "relevance": n["relevance"]}
            for n in news[:25]
        ],
        "knowledge_change": delta,
    }
    prompt = f"""You are a McKinsey-calibre Defence market strategist writing Accenture ANZ's \
monthly market-intelligence briefing for **{facts['window']['label']}**.

You are given STRUCTURED, PRE-COMPUTED data below. Every number and every news source is \
already verified — use ONLY these figures and these source URLs. Do NOT invent numbers, \
firms, or sources. Where you cite a contract, reference its cn_id; where you cite news, \
reference its url.

Follow this report structure:
{structure}

DATA (JSON):
{json.dumps(payload, default=str)}

Write in crisp, executive, insight-led prose (BLUF — lead with the "so what"). Use AUD \
magnitudes ($1.2B, $340M). The "Market Intelligence" section must weave in the \
knowledge_change figures (how much new intelligence arrived vs the prior period).

Respond with ONLY a JSON object (no fences):
{{
  "executive_summary": "3-5 sentence bottom-line-up-front",
  "contract_movements": "narrative for section 2 (competitor-focused)",
  "expenditure_trends": "narrative for section 3",
  "market_news": "narrative for section 4, incorporating what changed since last report",
  "implications": "section 5 — 3-5 sentence implications and watch-list for Accenture"
}}"""

    msg = _client().messages.create(
        model=model, max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    # Strip markdown fences the model sometimes wraps JSON in.
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1] if "```" in raw[3:] else raw[3:]
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {"executive_summary": raw, "contract_movements": "", "expenditure_trends": "",
            "market_news": "", "implications": ""}


def generate_report(session: Session, period_start: date, period_end: date, *,
                    model: str = "claude-sonnet-5", effort: str = "standard",
                    structure: str | None = None) -> MonthlyReport:
    if model not in _MODELS:
        model = "claude-sonnet-5"
    structure = (structure or DEFAULT_STRUCTURE).strip()

    # Anchor "what changed since last report" on the most recent prior report's time.
    prior_generated_at = session.execute(
        select(MonthlyReport.generated_at)
        .where((MonthlyReport.period_start != period_start) | (MonthlyReport.period_end != period_end))
        .order_by(MonthlyReport.generated_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    facts = build_facts(session, period_start, period_end)
    news = news_for_window(session, period_start, period_end)
    delta = knowledge_delta(session, prior_generated_at)
    narrative = synthesise(model, effort, facts, news, delta, structure)

    payload = {
        "structure": structure,
        "narrative": narrative,
        "facts": facts,
        "news": news,
        "knowledge_change": delta,
        "params": {"model": model, "effort": effort},
    }

    # Upsert on the period window (idempotent regeneration).
    existing = session.execute(
        select(MonthlyReport).where(
            MonthlyReport.period_start == period_start,
            MonthlyReport.period_end == period_end,
        )
    ).scalar_one_or_none()
    report = existing or MonthlyReport(period_start=period_start, period_end=period_end)
    report.generated_at = datetime.now(UTC)
    report.status = "draft"
    report.model = model
    report.effort = effort
    report.title = f"Defence Market Intelligence — {facts['window']['label']}"
    report.executive_summary = narrative.get("executive_summary", "")
    report.payload = payload
    report.contract_source_count = len(facts.get("contract_source_cn_ids", []))
    report.news_source_count = len(news)
    report.error = None
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


def _parse_args_period(args) -> tuple[date, date]:
    if args.month:
        year, month = (int(x) for x in args.month.split("-"))
        start = date(year, month, 1)
        end = date(year + (month // 12), (month % 12) + 1, 1)
        return start, end
    if args.from_ and args.to:
        return date.fromisoformat(args.from_), date.fromisoformat(args.to)
    return default_period()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a monthly market-intelligence report.")
    parser.add_argument("--month", help="YYYY-MM (whole calendar month)")
    parser.add_argument("--from", dest="from_", help="YYYY-MM-DD window start (inclusive)")
    parser.add_argument("--to", help="YYYY-MM-DD window end (exclusive)")
    parser.add_argument("--model", default="claude-sonnet-5", choices=sorted(_MODELS))
    parser.add_argument("--effort", default="standard", choices=list(_EFFORT_TOKENS))
    args = parser.parse_args()

    start, end = _parse_args_period(args)
    Session = get_session_factory()
    with Session() as session:
        report = generate_report(session, start, end, model=args.model, effort=args.effort)
    print(f"report #{report.id}: {report.title} "
          f"({report.contract_source_count} contract sources, {report.news_source_count} news items)")


if __name__ == "__main__":
    main()
