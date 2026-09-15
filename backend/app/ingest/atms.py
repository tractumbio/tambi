"""Approach-to-Market (ATM) ingestion — opportunity side (spec §8.3).

    python -m app.ingest.atms

The OCDS API is award-only, so live opportunities come from the AusTender website
(verified in Phase 0.4.1, see README.md). Two robots-allowed steps:

1. Fetch the current-ATM RSS list (`/public_data/rss/rss.xml`).
2. Enrich each ATM from its detail page (`/Atm/Show/{uuid}`), which embeds a small JSON
   blob (agency, UNSPSC code + title, type) plus HTML publish/close dates.

Raw-first (every response archived via ``RawStore``), upsert on ``atm_id``, and ATMs
that drop out of the current feed are marked ``closed`` — never deleted, since a
disappearing opportunity is a signal, not an error. Politely rate-limited with a
descriptive User-Agent.
"""

from __future__ import annotations

import argparse
import html as _html
import logging
import re
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import get_session_factory
from app.ingest.raw_store import LocalRawStore, RawStore
from app.ingest.transform import normalise_name
from app.models import Atm, IngestState, Organisation

logger = logging.getLogger("app.ingest.atms")

RSS_PATH = "/public_data/rss/rss.xml"
DETAIL_PATH = "/Atm/Show/{uuid}"
_ACT = ZoneInfo("Australia/Sydney")
_DEFENCE_KEYWORDS = ("defence", "military", "adf", "navy", "army", "air force", "aukus")


@dataclass
class RawAtm:
    atm_uuid: str
    source_ref: str
    rss_title: str
    rss_description: str
    # enriched from the detail page
    atm_id: str | None = None
    title: str | None = None
    agency_name: str | None = None
    atm_type: str | None = None
    unspsc_code: str | None = None
    unspsc_title: str | None = None
    published_date: date | None = None
    close_date: datetime | None = None
    location_state: str | None = None
    description: str | None = None


@dataclass
class AtmStats:
    fetched: int = 0
    upserted: int = 0
    defence: int = 0
    closed: int = 0
    skipped: int = 0

    def as_dict(self) -> dict[str, int]:
        return {"fetched": self.fetched, "upserted": self.upserted, "defence": self.defence,
                "closed": self.closed, "skipped": self.skipped}


# --- parsing helpers --------------------------------------------------------

def _uuid_from_link(link: str) -> str | None:
    m = re.search(r"/Atm/Show/([0-9a-fA-F-]{16,})", link)
    return m.group(1) if m else None


def _js(html: str, key: str) -> str | None:
    """Pull a value from the detail page's embedded JS object (single-quoted)."""
    m = re.search(rf"'{key}'\s*:\s*'((?:[^'\\]|\\.)*)'", html)
    if not m or not m.group(1).strip():
        return None
    return _html.unescape(m.group(1)).strip()


def _labelled(html: str, label: str) -> str | None:
    """Value that follows a ``Label :`` block in the detail HTML."""
    i = html.find(label)
    if i < 0:
        return None
    seg = re.sub(r"<[^>]+>", " ", html[i + len(label): i + len(label) + 200])
    seg = _html.unescape(seg)
    m = re.search(r":\s*([^\n]+?)\s{2,}", seg)
    return m.group(1).strip() if m else None


def _parse_close(text: str | None) -> datetime | None:
    if not text:
        return None
    m = re.search(r"(\d{1,2}-[A-Za-z]{3}-\d{4})\s+(\d{1,2}:\d{2}\s*[ap]m)", text, re.IGNORECASE)
    if not m:
        return None
    try:
        naive = datetime.strptime(f"{m.group(1)} {m.group(2).upper().replace(' ', '')}",
                                  "%d-%b-%Y %I:%M%p")
        return naive.replace(tzinfo=_ACT)
    except ValueError:
        return None


def _parse_date(text: str | None) -> date | None:
    if not text:
        return None
    m = re.search(r"\d{1,2}-[A-Za-z]{3}-\d{4}", text)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(0), "%d-%b-%Y").date()
    except ValueError:
        return None


def _is_defence(agency: str | None, title: str | None, desc: str | None) -> bool:
    hay = f"{agency or ''} {title or ''} {desc or ''}".lower()
    return any(k in hay for k in _DEFENCE_KEYWORDS)


class AtmClient:
    """Fetches the ATM RSS and detail pages, archiving every raw response."""

    def __init__(self, raw_store: RawStore | None = None) -> None:
        settings = get_settings()
        self._base = "https://www.tenders.gov.au"
        self._raw = raw_store or LocalRawStore()
        ua = settings.news_fetch_user_agent or (
            "Mozilla/5.0 (compatible; tambi-defence-intel/1.0; +research)"
        )
        self._delay = max(settings.news_min_request_interval_ms, 2000) / 1000
        self._client = httpx.Client(base_url=self._base, timeout=30.0,
                                    headers={"User-Agent": ua}, follow_redirects=True)

    def close(self) -> None:
        self._client.close()

    def _get(self, path: str, key: str) -> str:
        time.sleep(self._delay)
        resp = self._client.get(path)
        self._raw.put(key, resp.content)
        resp.raise_for_status()
        return resp.text

    def fetch_rss(self) -> list[RawAtm]:
        stamp = datetime.now(UTC).strftime("%Y-%m-%d")
        xml = self._get(RSS_PATH, f"atms/rss_{stamp}.xml")
        root = ElementTree.fromstring(xml)
        out: list[RawAtm] = []
        for item in root.iterfind(".//item"):
            link = (item.findtext("link") or "").strip()
            uuid = _uuid_from_link(link)
            if not uuid:
                continue
            out.append(RawAtm(
                atm_uuid=uuid, source_ref=(item.findtext("guid") or link).strip(),
                rss_title=(item.findtext("title") or "").strip(),
                rss_description=re.sub(r"<[^>]+>", " ", item.findtext("description") or "").strip(),
            ))
        return out

    def enrich(self, atm: RawAtm) -> RawAtm:
        html = self._get(DETAIL_PATH.format(uuid=atm.atm_uuid), f"atms/detail_{atm.atm_uuid}.html")
        atm.atm_id = _js(html, "atmID") or atm.rss_title.split(":", 1)[0].strip()
        atm.title = _js(html, "atmTitle") or atm.rss_title.split(":", 1)[-1].strip()
        atm.agency_name = _js(html, "atmAgencyName")
        atm.atm_type = _js(html, "atmType")
        atm.unspsc_code = _js(html, "atmCategoryCode")
        atm.unspsc_title = _js(html, "atmCategoryTitle")
        atm.location_state = _js(html, "atmLocationState")
        atm.close_date = _parse_close(_labelled(html, "Close Date"))
        atm.published_date = _parse_date(_labelled(html, "Publish Date"))
        atm.description = atm.rss_description or atm.title
        return atm


class AtmLoader:
    """Upserts ATMs on ``atm_id`` and resolves agencies to organisations."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._org_cache: dict[str, int] = {}
        self.stats = AtmStats()

    def _resolve_agency(self, name: str | None) -> int | None:
        if not name:
            return None
        key = normalise_name(name)
        if key in self._org_cache:
            return self._org_cache[key]
        org = self._session.execute(
            select(Organisation).where(Organisation.name_normalised == key)
        ).scalar_one_or_none()
        if org is None:
            org = Organisation(name=name, name_normalised=key, roles=["procuringEntity"])
            self._session.add(org)
            self._session.flush()
        self._org_cache[key] = org.id
        return org.id

    def upsert(self, raw: RawAtm) -> None:
        if not raw.atm_id:
            self.stats.skipped += 1
            return
        now = datetime.now(UTC)
        defence = _is_defence(raw.agency_name, raw.title, raw.description)
        existing = self._session.execute(
            select(Atm).where(Atm.atm_id == raw.atm_id)
        ).scalar_one_or_none()
        agency_id = self._resolve_agency(raw.agency_name)
        values = dict(
            atm_uuid=raw.atm_uuid, agency_org_id=agency_id, agency_name=raw.agency_name,
            title=raw.title, description=raw.description, atm_type=raw.atm_type,
            unspsc_code=raw.unspsc_code, unspsc_title=raw.unspsc_title,
            published_date=raw.published_date, close_date=raw.close_date,
            location_state=raw.location_state, is_defence=defence, status="open",
            source_ref=raw.source_ref, last_seen_at=now,
        )
        if existing is None:
            self._session.add(Atm(atm_id=raw.atm_id, first_seen_at=now, **values))
        else:
            for k, v in values.items():
                setattr(existing, k, v)
        self.stats.upserted += 1
        if defence:
            self.stats.defence += 1

    def mark_absent_closed(self, seen_ids: set[str]) -> None:
        """ATMs previously open but not in this fetch are closed (spec §8.3)."""
        result = self._session.execute(
            update(Atm).where(Atm.status == "open", Atm.atm_id.notin_(seen_ids or {""}))
            .values(status="closed")
        )
        self.stats.closed = result.rowcount or 0


def _update_state(session: Session, stats: AtmStats, status: str, error: str | None = None) -> None:
    state = session.get(IngestState, "atms")
    if state is None:
        state = IngestState(job_name="atms", records_processed=0)
        session.add(state)
    state.last_run_at = datetime.now(UTC)
    state.last_run_status = status
    state.records_processed = stats.upserted
    state.error_message = error


def run() -> AtmStats:
    session = get_session_factory()()
    client = AtmClient()
    loader = AtmLoader(session)
    try:
        items = client.fetch_rss()
        loader.stats.fetched = len(items)
        logger.info("atm rss fetched", extra={"count": len(items)})
        seen: set[str] = set()
        for raw in items:
            try:
                client.enrich(raw)
            except httpx.HTTPError as exc:
                logger.warning("atm detail failed", extra={"uuid": raw.atm_uuid, "error": str(exc)})
            loader.upsert(raw)
            if raw.atm_id:
                seen.add(raw.atm_id)
            session.commit()
        loader.mark_absent_closed(seen)
        _update_state(session, loader.stats, "success")
        session.commit()
        return loader.stats
    except Exception as exc:
        session.rollback()
        _update_state(session, loader.stats, "error", str(exc)[:2000])
        session.commit()
        raise
    finally:
        client.close()
        session.close()


def main() -> None:
    configure_logging()
    argparse.ArgumentParser(description="Ingest AusTender Approaches to Market.").parse_args()
    stats = run()
    print("ATM ingestion complete:", stats.as_dict())


if __name__ == "__main__":
    main()
