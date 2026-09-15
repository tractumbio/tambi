"""Load the reference-project capability corpus into the database.

Upserts by (firm_slug, title) so editing ``reference_projects_seed.yaml`` and re-running
is idempotent. Run:  python -m app.processing.load_reference_projects
"""

from __future__ import annotations

from pathlib import Path

import yaml
from sqlalchemy import select

from app.db.session import get_session_factory
from app.models import ReferenceProject
from app.processing.capability import invalidate_cache

_SEED_PATH = Path(__file__).with_name("reference_projects_seed.yaml")
_DEFAULT_SOURCE = "Public capability profile (illustrative — replace with verified records)"


def load() -> tuple[int, int]:
    with _SEED_PATH.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    firms: dict = data.get("firms", {})
    Session = get_session_factory()
    inserted = updated = 0

    with Session() as session:
        for firm_slug, entries in firms.items():
            for entry in entries or []:
                title = entry["title"]
                existing = session.execute(
                    select(ReferenceProject).where(
                        ReferenceProject.firm_slug == firm_slug,
                        ReferenceProject.title == title,
                    )
                ).scalar_one_or_none()

                if existing is None:
                    session.add(ReferenceProject(
                        firm_slug=firm_slug,
                        title=title,
                        description=entry["description"],
                        location=entry.get("location"),
                        client=entry.get("client"),
                        year=entry.get("year"),
                        source=entry.get("source", _DEFAULT_SOURCE),
                    ))
                    inserted += 1
                else:
                    existing.description = entry["description"]
                    existing.location = entry.get("location")
                    existing.client = entry.get("client")
                    existing.year = entry.get("year")
                    existing.source = entry.get("source", _DEFAULT_SOURCE)
                    updated += 1

        session.commit()

    invalidate_cache()  # force centroids to rebuild with the new corpus
    return inserted, updated


if __name__ == "__main__":
    ins, upd = load()
    print(f"reference_projects: {ins} inserted, {upd} updated")
