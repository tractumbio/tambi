"""Load parsed OCDS releases into the normalised tables (spec Phase 3/4 bridge).

This is the single write path shared by the backfill and incremental pipelines
(Phase 4). It owns the three things the transform deliberately does not: organisation
deduplication, the current-state contract upsert, and theme/competitor enrichment.

Idempotency (spec 7.4, 8.2) is anchored on ``raw_releases.release_id`` being unique:
a release already in the landing table is skipped whole, so re-running over the same
corpus creates no duplicate organisations, no double-counted amendments and no
duplicate theme rows. A genuinely new release under an existing ``ocid`` is treated
as an amendment — it updates the current-state row and increments ``amendment_count``
rather than inserting a second contract.

Deterministic (keyword/UNSPSC) theme rows are replaced on each refresh so a changed
rule set re-runs cleanly; ``manual`` and ``llm`` classifications are left untouched.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingest.transform import ParsedContract, ParsedParty, annualised_value, parse_release
from app.models import CompetitorGroup, Contract, ContractTheme, Organisation, RawRelease, Theme
from app.processing import competitors, service_offerings, themes

logger = logging.getLogger("app.ingest.loader")

# Tier-1 methods this loader owns and may replace on refresh; manual/llm are preserved.
_DETERMINISTIC_METHODS = ("keyword", "unspsc")


@dataclass
class LoadStats:
    releases_seen: int = 0
    landed_raw: int = 0  # releases written to raw_releases (the full-dataset landing layer)
    inserted: int = 0
    amended: int = 0
    skipped: int = 0  # release_id already present (idempotent no-op)
    skipped_non_defence: int = 0  # landed as raw only; not built into the analytics layer
    orgs_created: int = 0
    defence_contracts: int = 0
    theme_assignments: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "releases_seen": self.releases_seen,
            "landed_raw": self.landed_raw,
            "inserted": self.inserted,
            "amended": self.amended,
            "skipped": self.skipped,
            "skipped_non_defence": self.skipped_non_defence,
            "orgs_created": self.orgs_created,
            "defence_contracts": self.defence_contracts,
            "theme_assignments": self.theme_assignments,
        }


class Loader:
    """Stateful loader for a single ingest run.

    Holds per-run organisation caches so repeated parties within a run resolve to
    one row without redundant DB round-trips. Reference-table lookups
    (competitor groups, themes) are loaded once.
    """

    def __init__(self, session: Session, *, defence_only: bool = False) -> None:
        self._session = session
        # Default False: every release is stored and tagged via the ``is_defence`` flag,
        # so the warehouse holds the full portfolio and Defence analytics stay clean by
        # filtering on ``is_defence`` (non-Defence rows are kept, not discarded).
        # When True, non-Defence releases are filtered out before any Postgres write so
        # only the Defence portfolio lands. See spec Section 7.1 for the is_defence rules.
        self._defence_only = defence_only
        self._by_abn: dict[str, int] = {}
        self._by_name: dict[str, int] = {}  # only for orgs without an ABN
        # ocid -> Contract for rows touched this run. Needed because the session runs
        # with autoflush off, so a pending (unflushed) contract is invisible to
        # session.get — an original + amendment in the same fetch window would
        # otherwise both insert and collide on the ocid PK.
        self._contracts: dict[str, Contract] = {}
        self._group_ids: dict[str, int] = {
            slug: gid
            for slug, gid in session.execute(
                select(CompetitorGroup.slug, CompetitorGroup.id)
            ).all()
        }
        self._theme_ids: dict[str, int] = {
            slug: tid for slug, tid in session.execute(select(Theme.slug, Theme.id)).all()
        }
        self.stats = LoadStats()

    # -- Organisation dedup --------------------------------------------------

    def _resolve_org(self, party: ParsedParty) -> int:
        """Return the organisation id for a party, creating or updating as needed.

        Dedup: ABN first where present, ``name_normalised`` second (spec Section 6).
        Roles accumulate across appearances; the competitor group is assigned on
        creation from the supplier mapping (unmatched -> ``other``).
        """
        if party.abn:
            cached = self._by_abn.get(party.abn)
            if cached is not None:
                self._merge_roles(cached, party.roles)
                return cached
            existing = self._session.execute(
                select(Organisation).where(Organisation.abn == party.abn)
            ).scalar_one_or_none()
            if existing is not None:
                self._by_abn[party.abn] = existing.id
                self._merge_roles(existing.id, party.roles)
                return existing.id
            return self._create_org(party)

        key = party.name_normalised
        cached = self._by_name.get(key)
        if cached is not None:
            self._merge_roles(cached, party.roles)
            return cached
        existing = self._session.execute(
            select(Organisation).where(
                Organisation.abn.is_(None), Organisation.name_normalised == key
            )
        ).scalar_one_or_none()
        if existing is not None:
            self._by_name[key] = existing.id
            self._merge_roles(existing.id, party.roles)
            return existing.id
        return self._create_org(party)

    def _create_org(self, party: ParsedParty) -> int:
        group_slug = competitors.map_supplier(party.name_normalised, party.abn)
        org = Organisation(
            abn=party.abn,
            name=party.name,
            name_normalised=party.name_normalised,
            roles=sorted(set(party.roles)) or None,
            competitor_group_id=self._group_ids.get(group_slug),
        )
        self._session.add(org)
        self._session.flush()  # assign PK
        if party.abn:
            self._by_abn[party.abn] = org.id
        else:
            self._by_name[party.name_normalised] = org.id
        self.stats.orgs_created += 1
        return org.id

    def _merge_roles(self, org_id: int, roles: list[str]) -> None:
        if not roles:
            return
        org = self._session.get(Organisation, org_id)
        if org is None:
            return
        merged = set(org.roles or []) | set(roles)
        if merged != set(org.roles or []):
            org.roles = sorted(merged)

    # -- Contract upsert -----------------------------------------------------

    def load_release(self, parsed: ParsedContract, *, source_file: str | None = None) -> str:
        """Load one parsed release.

        Returns ``inserted`` | ``amended`` | ``skipped`` | ``filtered``. Non-Defence
        releases are filtered out **before** anything is written to Postgres when
        ``defence_only`` is set, so the database holds only the Defence portfolio. The
        full AusTender response still lives in the on-disk raw archive (``data/raw``),
        which remains the complete audit trail for reprocessing.
        """
        self.stats.releases_seen += 1

        already = self._session.execute(
            select(RawRelease.id).where(RawRelease.release_id == parsed.release_id)
        ).scalar_one_or_none()
        if already is not None:
            self.stats.skipped += 1
            return "skipped"

        scoping = themes.score_defence(parsed)
        existing = self._get_contract(parsed.ocid)

        # Filter to the Defence portfolio before touching Postgres: a new, non-Defence
        # contract is dropped entirely (no raw_releases row). An amendment to an
        # already-tracked (Defence) contract is still applied so its state stays correct.
        if existing is None and self._defence_only and not scoping.is_defence:
            self.stats.skipped_non_defence += 1
            return "filtered"

        # Land the release in the raw layer (Defence-scoped when defence_only is set).
        self._session.add(
            RawRelease(
                ocid=parsed.ocid,
                release_id=parsed.release_id,
                release_date=parsed.release_date,
                tags=parsed.tags or None,
                payload=parsed.payload,
                source_file=source_file,
            )
        )
        self.stats.landed_raw += 1

        now = datetime.now(UTC)
        buyer_id = self._resolve_org(parsed.buyer) if parsed.buyer else None
        supplier_id = self._resolve_org(parsed.supplier) if parsed.supplier else None

        if existing is None:
            self._insert_contract(parsed, buyer_id, supplier_id, now, scoping)
            self.stats.inserted += 1
            return "inserted"

        self._amend_contract(existing, parsed, buyer_id, supplier_id, now, scoping)
        self.stats.amended += 1
        return "amended"

    def _get_contract(self, ocid: str) -> Contract | None:
        """Cache-aware contract lookup (see the note on ``self._contracts``)."""
        if ocid in self._contracts:
            return self._contracts[ocid]
        found = self._session.get(Contract, ocid)
        if found is not None:
            self._contracts[ocid] = found
        return found

    def _insert_contract(
        self,
        parsed: ParsedContract,
        buyer_id: int | None,
        supplier_id: int | None,
        now: datetime,
        scoping: themes.DefenceScoping,
    ) -> None:
        svc = self._classify_offering(parsed)
        contract = Contract(
            ocid=parsed.ocid,
            cn_id=parsed.cn_id,
            title=parsed.title,
            description=parsed.description,
            buyer_org_id=buyer_id,
            supplier_org_id=supplier_id,
            value_amount=parsed.value_amount,
            value_currency=parsed.value_currency,
            date_published=parsed.date_published,
            date_signed=parsed.date_signed,
            period_start=parsed.period_start,
            period_end=parsed.period_end,
            procurement_method=parsed.procurement_method,
            unspsc_code=parsed.unspsc_code,
            unspsc_title=parsed.unspsc_title,
            buyer_division=parsed.buyer_division,
            buyer_branch=parsed.buyer_branch,
            is_defence=scoping.is_defence,
            service_offering=svc.service_offering,
            is_addressable=svc.is_addressable,
            service_offering_confidence=svc.confidence,
            value_per_year=annualised_value(
                parsed.value_amount, parsed.period_start, parsed.period_end
            ),
            amendment_count=0,
            first_seen_at=now,
            last_updated_at=now,
            latest_release_id=parsed.release_id,
        )
        self._session.add(contract)
        self._contracts[parsed.ocid] = contract
        self._log_scoping(parsed.ocid, scoping)
        if scoping.is_defence:
            self.stats.defence_contracts += 1
        self._refresh_themes(parsed)

    def _amend_contract(
        self,
        existing: Contract,
        parsed: ParsedContract,
        buyer_id: int | None,
        supplier_id: int | None,
        now: datetime,
        scoping: themes.DefenceScoping,
    ) -> None:
        """A new release under an existing ocid — an amendment (spec 8.2).

        Always counts and stamps. Current-state fields are only overwritten when this
        release is at least as recent as the stored state, so an out-of-order older
        release cannot clobber newer data.
        """
        existing.amendment_count = (existing.amendment_count or 0) + 1
        existing.last_updated_at = now

        if _is_newer(parsed.release_date, existing.date_published):
            existing.cn_id = parsed.cn_id
            existing.title = parsed.title
            existing.description = parsed.description
            existing.buyer_org_id = buyer_id
            existing.supplier_org_id = supplier_id
            existing.value_amount = parsed.value_amount
            existing.value_currency = parsed.value_currency
            existing.date_published = parsed.date_published
            existing.date_signed = parsed.date_signed
            existing.period_start = parsed.period_start
            existing.period_end = parsed.period_end
            existing.procurement_method = parsed.procurement_method
            existing.unspsc_code = parsed.unspsc_code
            existing.unspsc_title = parsed.unspsc_title
            existing.buyer_division = parsed.buyer_division
            existing.buyer_branch = parsed.buyer_branch
            existing.latest_release_id = parsed.release_id
            existing.is_defence = scoping.is_defence
            svc = self._classify_offering(parsed)
            existing.service_offering = svc.service_offering
            existing.is_addressable = svc.is_addressable
            existing.service_offering_confidence = svc.confidence
            existing.value_per_year = annualised_value(
                parsed.value_amount, parsed.period_start, parsed.period_end
            )
            self._log_scoping(parsed.ocid, scoping)
            self._refresh_themes(parsed)

    @staticmethod
    def _classify_offering(parsed: ParsedContract) -> service_offerings.ServiceClassification:
        return service_offerings.classify_service_offering(
            title=parsed.title,
            description=parsed.description,
            supplier_name=parsed.supplier.name if parsed.supplier else None,
            unspsc_code=parsed.unspsc_code,
        )

    # -- Theme rows ----------------------------------------------------------

    def _refresh_themes(self, parsed: ParsedContract) -> None:
        """Replace this contract's deterministic theme rows with the current matches.

        Manual/LLM classifications are preserved. Idempotent: same input yields the
        same rows, and a changed rule set re-runs cleanly.
        """
        # Flush first so any theme rows added earlier this run (e.g. an original that
        # an amendment in the same window supersedes) are visible to the DELETE below;
        # the session runs with autoflush off, so pending rows are otherwise invisible.
        self._session.flush()
        self._session.query(ContractTheme).filter(
            ContractTheme.ocid == parsed.ocid,
            ContractTheme.method.in_(_DETERMINISTIC_METHODS),
        ).delete(synchronize_session=False)

        for match in themes.classify_themes(parsed):
            theme_id = self._theme_ids.get(match.theme_slug)
            if theme_id is None:
                logger.warning("unknown theme slug from rules", extra={"slug": match.theme_slug})
                continue
            self._session.add(
                ContractTheme(
                    ocid=parsed.ocid,
                    theme_id=theme_id,
                    confidence=match.confidence,
                    method=match.method,
                )
            )
            self.stats.theme_assignments += 1

    def _log_scoping(self, ocid: str, scoping: themes.DefenceScoping) -> None:
        logger.info(
            "defence scoping",
            extra={
                "ocid": ocid,
                "is_defence": scoping.is_defence,
                "reasons": list(scoping.reasons),
            },
        )


def load_raw_package(
    session: Session,
    package: dict[str, Any],
    *,
    source_file: str | None = None,
    defence_only: bool = True,
) -> LoadStats:
    """Parse and load every release in an OCDS release package."""
    loader = Loader(session, defence_only=defence_only)
    for release in package.get("releases", []):
        parsed = parse_release(release)
        if parsed is None:
            continue
        loader.load_release(parsed, source_file=source_file)
    return loader.stats


def _is_newer(candidate: datetime | None, current: datetime | None) -> bool:
    if candidate is None:
        return False
    if current is None:
        return True
    return candidate >= current
