"""Historical backfill of AusTender contract notices (spec Phase 4.1).

    python -m app.ingest.backfill --from 2021-09-15 --to 2026-09-15

Walks the requested window one **month** at a time (the client subdivides each month
into daily requests internally, since the API has no cursor pagination). After every
month chunk the watermark in ``ingest_state`` is advanced and the session committed,
so a crash mid-backfill **resumes** from the last completed chunk rather than
restarting. Idempotency is guaranteed by the loader (``raw_releases.release_id`` is
unique), so re-processing an interrupted chunk creates no duplicates.

Uses ``contractPublished`` as the date type — the right signal for "what was awarded
in this window". Incremental delta loads (Phase 4.2) use ``contractLastModified``.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core.logging import configure_logging
from app.db.session import get_session_factory
from app.ingest.client import AusTenderClient
from app.ingest.loader import Loader
from app.ingest.transform import parse_release
from app.models import IngestState

logger = logging.getLogger("app.ingest.backfill")

JOB_NAME = "backfill"
DATE_TYPE = "contractPublished"
# Commit within a month at this cadence so a busy month is not one giant transaction.
_SUBBATCH_COMMIT = 500


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _next_month(d: date) -> date:
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


def _month_chunks(start: date, end: date) -> list[tuple[date, date]]:
    """Consecutive [chunk_start, chunk_end) month windows spanning [start, end)."""
    chunks: list[tuple[date, date]] = []
    cursor = start
    while cursor < end:
        nxt = min(_next_month(_month_start(cursor)), end)
        chunks.append((cursor, nxt))
        cursor = nxt
    return chunks


def _parse_cli_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC).date()


def _load_state(session: Session) -> IngestState:
    state = session.get(IngestState, JOB_NAME)
    if state is None:
        state = IngestState(job_name=JOB_NAME, records_processed=0)
        session.add(state)
        session.flush()
    return state


def _resume_start(state: IngestState, requested_start: date) -> date:
    """Resume from the last completed chunk if it is within the requested window."""
    if state.last_release_date is None:
        return requested_start
    watermark = state.last_release_date.date()
    return max(requested_start, watermark)


async def run_backfill(start: date, end: date, *, reset: bool = False) -> None:
    session = get_session_factory()()
    loader = Loader(session)  # one loader across the run keeps org caches warm
    try:
        state = _load_state(session)
        if reset:
            state.last_release_date = None
            state.records_processed = 0
            session.commit()

        effective_start = _resume_start(state, start)
        if effective_start >= end:
            logger.info(
                "backfill already complete for window",
                extra={"requested_from": str(start), "to": str(end),
                       "watermark": str(state.last_release_date)},
            )
            print(f"Nothing to do — watermark {state.last_release_date} already at/after {end}.")
            return

        chunks = _month_chunks(effective_start, end)
        logger.info(
            "backfill starting",
            extra={"from": str(effective_start), "to": str(end), "chunks": len(chunks)},
        )
        print(f"Backfill {effective_start} → {end} in {len(chunks)} monthly chunks.")

        async with AusTenderClient() as client:
            for idx, (c_start, c_end) in enumerate(chunks, 1):
                chunk_started = time.perf_counter()
                fetched = 0
                since_commit = 0
                async for release in client.fetch_releases(
                    c_start, c_end, date_type=DATE_TYPE
                ):
                    fetched += 1
                    parsed = parse_release(release)
                    if parsed is None:
                        continue
                    loader.load_release(parsed, source_file=f"backfill/{c_start}_{c_end}")
                    since_commit += 1
                    if since_commit >= _SUBBATCH_COMMIT:
                        session.commit()
                        since_commit = 0

                # Chunk complete: advance the watermark and checkpoint.
                state.last_release_date = datetime(
                    c_end.year, c_end.month, c_end.day, tzinfo=UTC
                )
                state.last_run_at = datetime.now(UTC)
                state.last_run_status = "running"
                state.records_processed = loader.stats.inserted + loader.stats.amended
                session.commit()

                elapsed = time.perf_counter() - chunk_started
                logger.info(
                    "chunk complete",
                    extra={
                        "chunk": f"{c_start}..{c_end}",
                        "index": idx,
                        "of": len(chunks),
                        "fetched": fetched,
                        "inserted_total": loader.stats.inserted,
                        "amended_total": loader.stats.amended,
                        "elapsed_s": round(elapsed, 1),
                    },
                )
                print(
                    f"[{idx}/{len(chunks)}] {c_start}..{c_end}  fetched={fetched}  "
                    f"ins={loader.stats.inserted} amd={loader.stats.amended} "
                    f"orgs={loader.stats.orgs_created} defence={loader.stats.defence_contracts}  "
                    f"({elapsed:.1f}s)",
                    flush=True,
                )

        state.last_run_status = "success"
        session.commit()
        print("Backfill complete:", loader.stats.as_dict())
        logger.info("backfill complete", extra=loader.stats.as_dict())
    except Exception as exc:  # checkpoint the failure so resume is possible
        session.rollback()
        state = _load_state(session)
        state.last_run_status = "error"
        state.error_message = str(exc)[:2000]
        state.last_run_at = datetime.now(UTC)
        session.commit()
        logger.exception("backfill failed", extra={"error": str(exc)})
        raise
    finally:
        session.close()


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Backfill AusTender history into Postgres.")
    parser.add_argument("--from", dest="date_from", required=True, help="YYYY-MM-DD (inclusive)")
    parser.add_argument("--to", dest="date_to", required=True, help="YYYY-MM-DD (exclusive)")
    parser.add_argument(
        "--reset", action="store_true", help="Ignore any saved watermark and start from --from."
    )
    args = parser.parse_args()
    asyncio.run(
        run_backfill(
            _parse_cli_date(args.date_from), _parse_cli_date(args.date_to), reset=args.reset
        )
    )


if __name__ == "__main__":
    main()
