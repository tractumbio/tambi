"""Recompute derived classifications over the contracts already in Postgres.

    python -m app.processing.reprocess [--only service-offering]

Idempotent, DB-only (no API calls): re-runs the enrichment rules over the current
``contracts`` rows and writes the results back. Use it after changing the classifier
rules so the analytics layer reflects them without a re-fetch. Currently recomputes the
service-offering / addressability / annualised-value fields.
"""

from __future__ import annotations

import argparse
from collections import Counter

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.logging import configure_logging
from app.db.session import get_session_factory
from app.ingest.transform import _extract_buyer_unit, annualised_value
from app.models import CompetitorGroup, Contract, Organisation, RawRelease
from app.processing import competitors
from app.processing.service_offerings import classify_service_offering

_BATCH = 1000


def reprocess_service_offerings(session: Session) -> Counter[str]:
    rows = session.execute(
        select(
            Contract.ocid,
            Contract.title,
            Contract.description,
            Contract.unspsc_code,
            Contract.value_amount,
            Contract.period_start,
            Contract.period_end,
            Organisation.name.label("supplier_name"),
        ).outerjoin(Organisation, Organisation.id == Contract.supplier_org_id)
    ).all()

    tally: Counter[str] = Counter()
    for i, r in enumerate(rows, 1):
        svc = classify_service_offering(
            title=r.title,
            description=r.description,
            supplier_name=r.supplier_name,
            unspsc_code=r.unspsc_code,
        )
        session.execute(
            update(Contract)
            .where(Contract.ocid == r.ocid)
            .values(
                service_offering=svc.service_offering,
                is_addressable=svc.is_addressable,
                service_offering_confidence=svc.confidence,
                value_per_year=annualised_value(r.value_amount, r.period_start, r.period_end),
            )
        )
        tally[svc.service_offering or "(non-addressable)"] += 1
        if i % _BATCH == 0:
            session.commit()
    session.commit()
    return tally


def reprocess_org_competitor_groups(session: Session) -> Counter[str]:
    """Re-map every organisation to a competitor group from the current rules.

    Run after adding groups/rules (e.g. the MBB firms) so existing organisations pick
    up their new group without a re-ingest.
    """
    group_ids = {
        slug: gid
        for slug, gid in session.execute(
            select(CompetitorGroup.slug, CompetitorGroup.id)
        ).all()
    }
    orgs = session.execute(
        select(Organisation.id, Organisation.name_normalised, Organisation.abn)
    ).all()
    tally: Counter[str] = Counter()
    for i, o in enumerate(orgs, 1):
        slug = competitors.map_supplier(o.name_normalised, o.abn)
        session.execute(
            update(Organisation)
            .where(Organisation.id == o.id)
            .values(competitor_group_id=group_ids.get(slug))
        )
        tally[slug] += 1
        if i % _BATCH == 0:
            session.commit()
    session.commit()
    return tally


def reprocess_buyer_units(session: Session) -> tuple[int, int]:
    """Backfill buyer division/branch from stored payloads (no API calls).

    Reads each contract's latest release payload from ``raw_releases`` and extracts the
    buyer org unit that ingestion previously discarded. Returns (updated, with_unit).
    """
    rows = session.execute(
        select(Contract.ocid, RawRelease.payload).join(
            RawRelease, RawRelease.release_id == Contract.latest_release_id
        )
    ).all()
    updated = with_unit = 0
    for i, r in enumerate(rows, 1):
        parties = (r.payload or {}).get("parties", [])
        division, branch = _extract_buyer_unit(parties)
        session.execute(
            update(Contract)
            .where(Contract.ocid == r.ocid)
            .values(buyer_division=division, buyer_branch=branch)
        )
        updated += 1
        if division or branch:
            with_unit += 1
        if i % _BATCH == 0:
            session.commit()
    session.commit()
    return updated, with_unit


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Recompute contract classifications in place.")
    parser.add_argument(
        "--only", default="all",
        choices=["all", "service-offering", "competitor-groups", "buyer-units"],
    )
    args = parser.parse_args()

    session = get_session_factory()()
    try:
        if args.only in ("all", "buyer-units"):
            updated, with_unit = reprocess_buyer_units(session)
            print(f"Buyer units: updated {updated} contracts, {with_unit} have a division/branch.")
        if args.only in ("all", "competitor-groups"):
            groups = reprocess_org_competitor_groups(session)
            mapped = sum(v for k, v in groups.items() if k != "other")
            print(f"Re-mapped {sum(groups.values())} organisations — {mapped} to a named group.")
            for slug, count in groups.most_common(10):
                print(f"  {count:>7}  {slug}")
        if args.only in ("all", "service-offering"):
            tally = reprocess_service_offerings(session)
            total = sum(tally.values())
            addressable = total - tally.get("(non-addressable)", 0)
            print(f"Reprocessed {total} contracts — {addressable} Accenture-addressable.")
            for offering, count in tally.most_common():
                print(f"  {count:>7}  {offering}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
