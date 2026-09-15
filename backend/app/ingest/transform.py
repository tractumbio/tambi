"""OCDS release → flat contract model (Phase 3 transform).

Pure functions, no database and no I/O, so this — the highest-value and most
error-prone surface in the pipeline — is unit-testable against the saved sample
response. The loader (Phase 4) turns a ``ParsedContract`` into ``organisations`` /
``contracts`` / ``raw_releases`` rows; org dedup and upserts live there, not here.

Mappings verified against the real feed (see ``ingest/README.md``):
- buyer role is ``procuringEntity`` (not ``buyer``);
- ``cn_id`` is ``contracts[].id`` (e.g. ``CN4273499``), distinct from ``ocid``;
- ``value.amount`` arrives as a *string* — cast to Decimal here;
- ``unspsc_title`` is absent from the feed — left ``None`` (reference-derived later);
- ``date_published`` comes from the release ``date``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

ABN_SCHEME = "AU-ABN"
UNSPSC_SCHEME = "UNSPSC"

# Sanity bounds for parsed dates. The AusTender feed carries junk sentinels
# (e.g. period end in year 0899) that must not reach the warehouse — anything
# outside this window is treated as missing. 2100 leaves genuine "open-ended"
# far-future end dates intact while rejecting clearly-corrupt values.
_MIN_YEAR = 1990
_MAX_YEAR = 2100

# Company suffixes / tokens stripped when normalising a name for dedup.
_SUFFIX_TOKENS = {
    "pty", "ltd", "limited", "proprietary", "inc", "incorporated", "llc", "llp",
    "plc", "co", "corp", "corporation", "company", "the", "group", "holdings",
    "australia", "australian", "aust",
}
_PUNCT_RE = re.compile(r"[^a-z0-9\s]")
_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ParsedParty:
    """A supplier or buyer extracted from OCDS ``parties``."""

    source_id: str | None
    name: str
    name_normalised: str
    abn: str | None
    roles: list[str]


@dataclass
class ParsedContract:
    """Flattened current-state contract plus the parties it references."""

    ocid: str
    release_id: str
    release_date: datetime | None
    tags: list[str]
    cn_id: str | None
    title: str | None
    description: str | None
    value_amount: Decimal | None
    value_currency: str | None
    date_published: datetime | None
    date_signed: datetime | None
    period_start: date | None
    period_end: date | None
    procurement_method: str | None
    unspsc_code: str | None
    unspsc_title: str | None
    # Buyer organisational unit — AusTender puts the buyer's procurement-officer contact
    # on a party's contactPoint (division = group e.g. "CASG", branch = the specific
    # command e.g. "JCG - Joint Logistics Command"). This is the real Defence branch data.
    buyer_division: str | None
    buyer_branch: str | None
    buyer: ParsedParty | None
    supplier: ParsedParty | None
    payload: dict[str, Any] = field(repr=False, default_factory=dict)


def annualised_value(
    value: Decimal | None, period_start: date | None, period_end: date | None
) -> Decimal | None:
    """Value spread over the contract term (the previous analytics' ``Value Per Year``).

    Multi-year contracts are divided by their duration in years; terms under a year
    keep the full value (never inflated). Returns ``None`` when value is missing.
    """
    if value is None:
        return None
    if not period_start or not period_end or period_end <= period_start:
        return value
    years = (period_end - period_start).days / 365.25
    if years <= 1.0:
        return value
    return (value / Decimal(str(years))).quantize(Decimal("0.01"))


def normalise_name(name: str | None) -> str:
    """Lowercase, strip punctuation and common company suffixes, collapse spaces.

    Used as the secondary dedup key when an ABN is absent. Deterministic and
    reversible enough to be inspectable — an MD may ask why two spellings merged.
    """
    if not name:
        return ""
    text = _PUNCT_RE.sub(" ", name.lower())
    tokens = [t for t in _WS_RE.sub(" ", text).strip().split(" ") if t and t not in _SUFFIX_TOKENS]
    return " ".join(tokens)


def _parse_datetime(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    result = parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    if not (_MIN_YEAR <= result.year <= _MAX_YEAR):
        return None
    return result


def _parse_date(value: Any) -> date | None:
    dt = _parse_datetime(value)
    return dt.date() if dt else None


def _parse_amount(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _extract_abn(party: dict[str, Any]) -> str | None:
    for ident in party.get("additionalIdentifiers") or []:
        if ident.get("scheme") == ABN_SCHEME and ident.get("id"):
            return str(ident["id"]).strip()
    return None


def _parse_party(party: dict[str, Any]) -> ParsedParty:
    name = (party.get("name") or "").strip()
    return ParsedParty(
        source_id=party.get("id"),
        name=name,
        name_normalised=normalise_name(name),
        abn=_extract_abn(party),
        roles=list(party.get("roles") or []),
    )


def _find_party_by_role(parties: list[dict[str, Any]], role: str) -> dict[str, Any] | None:
    for party in parties:
        if role in (party.get("roles") or []):
            return party
    return None


def _extract_unspsc(contract: dict[str, Any]) -> str | None:
    for item in contract.get("items") or []:
        classification = item.get("classification") or {}
        if classification.get("scheme") == UNSPSC_SCHEME and classification.get("id"):
            return str(classification["id"]).strip()
    return None


def _extract_buyer_unit(parties: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    """Return ``(division, branch)`` from the first party contactPoint that carries them.

    AusTender attaches the buyer's procurement-officer contact (with the buyer's
    ``division`` and ``branch``) to a party's ``contactPoint`` — in practice the supplier
    party. Both are the *buyer's* org unit, not the supplier's.
    """
    for party in parties:
        cp = party.get("contactPoint") or {}
        division = (cp.get("division") or "").strip() or None
        branch = (cp.get("branch") or "").strip() or None
        if division or branch:
            return division, branch
    return None, None


def parse_release(release: dict[str, Any]) -> ParsedContract | None:
    """Flatten a single OCDS release into a ``ParsedContract``.

    Returns ``None`` for releases with no ``contracts[]`` (nothing to model as a
    current-state contract). Only the first contract is taken — AusTender emits one
    contract per contract-notice process; multiples share the same ``ocid``.
    """
    ocid = release.get("ocid")
    release_id = release.get("id")
    if not ocid or not release_id:
        return None

    contracts = release.get("contracts") or []
    if not contracts:
        return None
    contract = contracts[0]

    parties = release.get("parties") or []
    buyer_party = _find_party_by_role(parties, "procuringEntity")
    supplier_party = _find_party_by_role(parties, "supplier")

    value = contract.get("value") or {}
    period = contract.get("period") or {}
    tender = release.get("tender") or {}
    buyer_division, buyer_branch = _extract_buyer_unit(parties)

    return ParsedContract(
        ocid=ocid,
        release_id=release_id,
        release_date=_parse_datetime(release.get("date")),
        tags=list(release.get("tag") or []),
        cn_id=contract.get("id"),
        title=contract.get("title"),
        description=contract.get("description"),
        value_amount=_parse_amount(value.get("amount")),
        value_currency=value.get("currency"),
        date_published=_parse_datetime(release.get("date")),
        date_signed=_parse_datetime(contract.get("dateSigned")),
        period_start=_parse_date(period.get("startDate")),
        period_end=_parse_date(period.get("endDate")),
        procurement_method=tender.get("procurementMethod"),
        unspsc_code=_extract_unspsc(contract),
        unspsc_title=None,  # not in the feed; populated later from a reference table
        buyer_division=buyer_division,
        buyer_branch=buyer_branch,
        buyer=_parse_party(buyer_party) if buyer_party else None,
        supplier=_parse_party(supplier_party) if supplier_party else None,
        payload=release,
    )
