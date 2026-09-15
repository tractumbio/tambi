"""Report-side reader over the accumulating knowledge base.

Reads stored ``knowledge_items`` for a report window and computes how much the corpus has
changed since the previous period — the "what's new since last time" signal the report
surfaces. All deterministic; no LLM here (gathering happens in ``harvest_news``).
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import KnowledgeItem


def _dt(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


def _item_dict(k: KnowledgeItem, *, is_new: bool) -> dict:
    return {
        "headline": k.headline,
        "summary": k.summary,
        "url": k.url,
        "category": k.category,
        "relevance": k.relevance,
        "entities": list(k.entities) if k.entities else [],
        "published_date": k.published_date.isoformat() if k.published_date else None,
        "first_seen_at": k.first_seen_at.isoformat() if k.first_seen_at else None,
        "is_new": is_new,
    }


def news_for_window(session: Session, start: date, end: date, *, limit: int = 40) -> list[dict]:
    """Knowledge items *published* in the window (period-relevant news).

    Membership is keyed on ``published_date`` (falling back to the discovery date when a
    source carries no publish date). Each item is flagged ``is_new`` when it was first
    accumulated during the window — i.e. genuinely new intelligence since the last report.
    """
    # published_date in window, OR (no published_date AND discovered in window)
    published_in = (
        (KnowledgeItem.published_date >= start) & (KnowledgeItem.published_date < end)
    )
    discovered_in = (
        KnowledgeItem.published_date.is_(None)
        & (KnowledgeItem.first_seen_at >= _dt(start))
        & (KnowledgeItem.first_seen_at < _dt(end))
    )
    rows = session.execute(
        select(KnowledgeItem)
        .where(published_in | discovered_in)
        .order_by(KnowledgeItem.published_date.desc().nullslast(),
                  KnowledgeItem.first_seen_at.desc())
        .limit(limit)
    ).scalars().all()
    return [
        _item_dict(k, is_new=(k.first_seen_at is not None and _dt(start) <= k.first_seen_at < _dt(end)))
        for k in rows
    ]


def _count(session: Session, start: date, end: date) -> int:
    return int(session.execute(
        select(func.count()).select_from(KnowledgeItem)
        .where(KnowledgeItem.first_seen_at >= _dt(start), KnowledgeItem.first_seen_at < _dt(end))
    ).scalar_one())


def knowledge_delta(session: Session, since: datetime | None) -> dict:
    """Change in the knowledge base since the previous report was generated.

    ``since`` is the prior report's ``generated_at`` (None for the first-ever report, when
    the whole corpus counts as new). This is the "what changed since last time" signal.
    """
    total_corpus = int(session.execute(
        select(func.count()).select_from(KnowledgeItem)
    ).scalar_one())

    if since is not None:
        new_cond = KnowledgeItem.first_seen_at > since
        new_count = int(session.execute(
            select(func.count()).select_from(KnowledgeItem).where(new_cond)
        ).scalar_one())
        # Prior interval of equal length before `since`, for a like-for-like delta.
        interval = datetime.now(UTC) - since
        prev_cond = (
            (KnowledgeItem.first_seen_at > since - interval)
            & (KnowledgeItem.first_seen_at <= since)
        )
        prev_count = int(session.execute(
            select(func.count()).select_from(KnowledgeItem).where(prev_cond)
        ).scalar_one())
        delta_pct = round((new_count - prev_count) / prev_count * 100, 1) if prev_count > 0 else None
    else:
        new_cond = None
        new_count = total_corpus
        prev_count = 0
        delta_pct = None

    def _scope(stmt):
        return stmt.where(new_cond) if new_cond is not None else stmt

    by_category = {
        cat: int(cnt) for cat, cnt in session.execute(
            _scope(select(KnowledgeItem.category, func.count()).select_from(KnowledgeItem))
            .group_by(KnowledgeItem.category)
        ).all()
    }

    ent_rows = session.execute(
        _scope(
            select(func.unnest(KnowledgeItem.entities).label("slug"), func.count())
            .select_from(KnowledgeItem)
            .where(KnowledgeItem.entities.is_not(None))
        )
        .group_by("slug").order_by(func.count().desc()).limit(8)
    ).all()
    top_entities = [{"slug": r.slug, "count": int(r[1])} for r in ent_rows]

    return {
        "new_items": new_count,
        "prev_window_items": prev_count,
        "delta_pct": delta_pct,
        "total_corpus": total_corpus,
        "by_category": by_category,
        "top_entities": top_entities,
    }
