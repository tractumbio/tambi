"""Load the saved Phase 0 sample into the normalised tables (spec Phase 3 gate).

    python -m app.ingest.load_sample

Proves the Phase 3 done-when: the sample response loads into the normalised tables
and re-running is idempotent (the second pass reports every release skipped, no new
rows). Also prints the highest-value unmatched-supplier report (spec 7.3).

Reads the archived sample with utf-8-sig because the saved file carries a BOM; live
API responses do not.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.logging import configure_logging
from app.db.session import get_session_factory
from app.ingest.loader import load_raw_package
from app.processing.competitors import unmatched_supplier_report

_SAMPLE = Path(__file__).resolve().parents[3] / "data" / "raw" / "sample_response.json"


def main() -> None:
    configure_logging()
    package = json.loads(_SAMPLE.read_text(encoding="utf-8-sig"))
    source_file = str(_SAMPLE.relative_to(_SAMPLE.parents[3]))

    session = get_session_factory()()
    try:
        stats = load_raw_package(session, package, source_file=source_file)
        session.commit()
        print("Load stats:", stats.as_dict())

        report = unmatched_supplier_report(session, limit=15)
        print(f"\nTop {len(report)} unmatched Defence suppliers (mapped to 'other'):")
        for row in report:
            print(f"  ${row.total_value:>15,.2f}  ({row.contract_count:>3})  {row.name}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
