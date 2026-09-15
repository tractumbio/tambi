"""News harvester — accumulates the market-intelligence knowledge base.

Runs Claude's web-search tool across competitors / Australian Defence government / macro,
archives the raw response to disk (the "bucket"), and upserts structured items into the
``knowledge_items`` store (dedup on URL; new rows get ``first_seen_at`` = now, existing
rows bump ``last_seen_at``). Designed to be run on a schedule so the corpus grows over
time — reports then read the store and report on what has changed since last time.

CLI:  python -m app.intelligence.harvest_news [--effort low|standard|deep] [--model ...]
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.models import CompetitorGroup, IngestState, KnowledgeItem

_JOB = "news_harvest"
_DEFAULT_MODEL = "claude-haiku-4-5-20251001"

# effort -> (web-search max_uses, target item count)
_EFFORT = {"low": (5, 8), "standard": (9, 15), "deep": (14, 25)}

# Curated allowlist — intelligence is only pulled from these reputable outlets. Editable
# from the UI (stored in news_domains); this is the seed for a fresh install. Enforced
# BOTH via the web-search tool (allowed_domains) and on ingest.
REPUTABLE_DOMAINS = [
    # Government & policy
    "defence.gov.au",           # Australian Department of Defence
    "minister.defence.gov.au",  # Defence ministers
    "asa.gov.au",               # Australian Submarine Agency
    "aspi.org.au",              # Australian Strategic Policy Institute
    "asx.com.au",               # ASX company announcements / filings
    # Trade & general press
    "defenceconnect.com.au",    # Defence Connect
    "australiandefence.com.au", # Australian Defence Magazine
    "adbr.com.au",              # Australian Defence Business Review
    "consulting.com.au",        # Consulting.com.au
    "abc.net.au",               # ABC News
    "janes.com",                # Janes
    "breakingdefence.com",      # Breaking Defense
    "thediplomat.com",          # The Diplomat (Indo-Pacific security)
    # Official firm newsrooms (releases by assessed firms)
    "accenture.com", "deloitte.com", "kpmg.com", "ey.com", "pwc.com.au",
    "mckinsey.com", "bcg.com", "bain.com", "thalesgroup.com", "baesystems.com",
    "boeing.com", "lockheedmartin.com", "babcockinternational.com", "jacobs.com",
    "kbr.com", "leidos.com", "dxc.com", "ibm.com", "novasystems.com",
]


def get_allowed_domains(session: Session) -> list[str]:
    """Enabled domains from the DB allowlist, seeding it from the constant on first use."""
    from app.models import NewsDomain

    rows = session.execute(select(NewsDomain)).scalars().all()
    if not rows:
        for d in REPUTABLE_DOMAINS:
            session.add(NewsDomain(domain=d, enabled=True))
        session.commit()
        return list(REPUTABLE_DOMAINS)
    return [r.domain for r in rows if r.enabled]


def _host_allowed(url: str, domains: list[str]) -> bool:
    from urllib.parse import urlparse

    host = (urlparse(url).hostname or "").lower().lstrip(".")
    return any(host == d or host.endswith("." + d) for d in domains)

_KEY_COMPETITORS = (
    "Accenture, Deloitte, KPMG, EY, PwC, McKinsey, BCG, Bain, Leidos, DXC, IBM, "
    "Thales, BAE Systems, Boeing, Lockheed Martin, Babcock, Jacobs, KBR, Nova Systems"
)


@dataclass
class HarvestResult:
    fetched: int
    inserted: int
    updated: int
    archive_path: str | None


def _client():
    from app.llm.claude_client import get_anthropic_client
    return get_anthropic_client()


def _archive_dir() -> Path:
    # Mirrors the OCDS raw archive convention (settings.raw_store_path -> ./data/raw).
    base = Path(get_settings().raw_store_path).parent / "news_raw"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _web_search_items(model: str, effort: str, domains: list[str],
                      recency: str = "the last ~6 weeks") -> tuple[list[dict], str]:
    """Run the web search; return (items, raw_text)."""
    max_uses, target = _EFFORT.get(effort, _EFFORT["standard"])
    today = datetime.now(UTC).strftime("%d %B %Y")
    prompt = f"""You are a Defence market-intelligence analyst at Accenture ANZ. Today is {today}.

Use web search to find the most significant news from {recency} affecting the \
Australian Defence contracting market, across three areas:
1. COMPETITORS — M&A, major contract wins/losses, leadership or strategy moves by: {_KEY_COMPETITORS}. \
Prefer OFFICIAL sources where available: the firm's own newsroom/press release, and ASX \
announcements/filings for listed entities.
2. GOVERNMENT — Australian Defence policy, budget, strategy, procurement announcements (DSR, AUKUS, Defence portfolio).
3. MACRO — macroeconomic/geopolitical factors (defence spending, AUD, supply chains, alliances) moving this market.

Only use these reputable outlets: {", ".join(domains)}.

Find up to {target} distinct, material items. Respond with ONLY a JSON array (no prose, no \
fences). Each element:
{{"headline": "...", "summary": "1-2 factual sentences", "url": "https://real-source", \
"category": "competitor|government|macro", "published_date": "YYYY-MM-DD or null", \
"relevance": "1 sentence on why it matters to Accenture"}}
Every item MUST carry a real source url from one of the allowed outlets. Omit anything else."""

    # Some domains block Anthropic's crawler, which 400s the whole request. Strip the
    # offending domains reported in the error and retry until the call succeeds.
    allowed = list(domains)
    for _ in range(4):
        try:
            msg = _client().messages.create(
                model=model,
                max_tokens=6000,
                tools=[{
                    "type": "web_search_20250305", "name": "web_search",
                    "max_uses": max_uses, "allowed_domains": allowed,
                }],
                messages=[{"role": "user", "content": prompt}],
            )
            break
        except Exception as exc:  # noqa: BLE001
            blocked = re.findall(r"'([^']+\.[^']+)'", str(exc)) if "not accessible" in str(exc) else []
            remaining = [d for d in allowed if d not in blocked]
            if not blocked or not remaining or remaining == allowed:
                raise
            allowed = remaining
    raw_text = "".join(
        b.text for b in msg.content if getattr(b, "type", None) == "text"
    ).strip()
    return _parse_items(raw_text), raw_text


def _parse_items(text: str) -> list[dict]:
    if not text:
        return []
    if "```" in text:
        for part in text.split("```"):
            p = part.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("["):
                text = p
                break
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _competitor_index(session: Session) -> list[tuple[str, str]]:
    """(slug, lowercase label) for entity matching, excluding the 'other' bucket."""
    rows = session.execute(
        select(CompetitorGroup.slug, CompetitorGroup.label).where(CompetitorGroup.slug != "other")
    ).all()
    return [(r.slug, r.label.lower()) for r in rows]


def _match_entities(text: str, index: list[tuple[str, str]]) -> list[str]:
    low = text.lower()
    return [slug for slug, label in index if label and label in low]


def run_harvest(session: Session, *, model: str = _DEFAULT_MODEL, effort: str = "standard",
                recency: str = "the last ~6 weeks") -> HarvestResult:
    domains = get_allowed_domains(session)
    items, raw_text = _web_search_items(model, effort, domains, recency)

    # Archive the raw response to disk (the "bucket").
    archive_path: str | None = None
    if raw_text:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = _archive_dir() / f"harvest_{stamp}.json"
        path.write_text(json.dumps({"model": model, "effort": effort, "items": items,
                                    "raw_text": raw_text}, indent=2), encoding="utf-8")
        archive_path = str(path)

    comp_index = _competitor_index(session)
    existing_urls = set(session.execute(select(KnowledgeItem.url)).scalars().all())
    handled: set[str] = set()
    inserted = updated = 0
    now = datetime.now(UTC)

    for it in items:
        url = (it.get("url") or "").strip()
        if not url.startswith("http") or not _host_allowed(url, domains):
            continue  # only reputable, allowlisted sources are stored
        if url in handled:
            continue  # de-dupe within this batch
        handled.add(url)

        if url in existing_urls:
            row = session.execute(
                select(KnowledgeItem).where(KnowledgeItem.url == url)
            ).scalar_one()
            row.last_seen_at = now
            updated += 1
            continue

        headline = str(it.get("headline", "")).strip()
        summary = str(it.get("summary", "")).strip()
        category = it.get("category") if it.get("category") in {"competitor", "government", "macro"} else "macro"
        entities = _match_entities(f"{headline} {summary}", comp_index)
        session.add(KnowledgeItem(
            url=url, headline=headline, summary=summary, category=category,
            entities=entities or None, relevance=str(it.get("relevance", "")).strip() or None,
            published_date=_parse_date(it.get("published_date")), first_seen_at=now, last_seen_at=now,
            source_query=f"{effort} harvest", raw_path=archive_path, payload=it,
        ))
        inserted += 1

    # Record run state like the ingest jobs.
    state = session.get(IngestState, _JOB) or IngestState(job_name=_JOB)
    state.last_run_at = now
    state.last_run_status = "ok"
    state.records_processed = inserted
    session.add(state)
    session.commit()

    return HarvestResult(fetched=len(items), inserted=inserted, updated=updated, archive_path=archive_path)


def _parse_date(value) -> object | None:
    from datetime import date

    if not value or not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Harvest market-intelligence news into the knowledge base.")
    parser.add_argument("--effort", choices=list(_EFFORT), default="standard")
    parser.add_argument("--model", default=_DEFAULT_MODEL)
    parser.add_argument("--lookback-months", type=int, default=0,
                        help="Broaden the search window to N months (default: ~6 weeks)")
    args = parser.parse_args()

    recency = f"the last {args.lookback_months} months" if args.lookback_months else "the last ~6 weeks"
    Session = get_session_factory()
    with Session() as session:
        try:
            result = run_harvest(session, model=args.model, effort=args.effort, recency=recency)
        except Exception as exc:  # noqa: BLE001
            state = session.get(IngestState, _JOB) or IngestState(job_name=_JOB)
            state.last_run_at = datetime.now(UTC)
            state.last_run_status = "error"
            state.error_message = str(exc)[:500]
            session.add(state)
            session.commit()
            raise
    print(f"harvest: fetched={result.fetched} inserted={result.inserted} "
          f"updated={result.updated} archive={result.archive_path}")


if __name__ == "__main__":
    main()
