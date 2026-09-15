"""Supplier -> competitor group mapping (spec Section 7.3).

Rolls messy supplier entities into the MD-meaningful competitor groups seeded in
``competitor_groups``. Rules live in ``competitor_rules.yaml`` (no hardcoded lists
in code); everything unmatched falls to the ``other`` group. After each ingest run
the pipeline should surface the highest-value unmatched suppliers so the mapping
can be improved — :func:`unmatched_supplier_report` produces exactly that.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session

_RULES_PATH = Path(__file__).with_name("competitor_rules.yaml")

DEFAULT_GROUP_SLUG = "other"


@dataclass(frozen=True)
class _GroupRule:
    slug: str
    abns: frozenset[str]
    name_tokens: frozenset[str]
    name_contains: tuple[str, ...]


@functools.lru_cache(maxsize=1)
def _load_rules() -> tuple[_GroupRule, ...]:
    with _RULES_PATH.open(encoding="utf-8") as fh:
        data: dict[str, Any] = yaml.safe_load(fh)
    rules: list[_GroupRule] = []
    for group in data.get("groups", []):
        rules.append(
            _GroupRule(
                slug=group["slug"],
                abns=frozenset(str(a).replace(" ", "") for a in group.get("abns", [])),
                name_tokens=frozenset(t.lower() for t in group.get("name_tokens", [])),
                name_contains=tuple(c.lower() for c in group.get("name_contains", [])),
            )
        )
    return tuple(rules)


def map_supplier(name_normalised: str | None, abn: str | None) -> str:
    """Return the competitor-group slug for a supplier, or ``other`` if unmatched.

    ABN is the strongest signal and is checked first; then whole-word tokens; then
    substrings. Rules are evaluated in file order, so list more specific groups
    before broader ones if a name could plausibly hit two.
    """
    normalised = (name_normalised or "").lower()
    tokens = set(normalised.split())
    abn_key = (abn or "").replace(" ", "")

    for rule in _load_rules():
        if abn_key and abn_key in rule.abns:
            return rule.slug
    for rule in _load_rules():
        if rule.name_tokens & tokens:
            return rule.slug
        if any(fragment in normalised for fragment in rule.name_contains):
            return rule.slug
    return DEFAULT_GROUP_SLUG


@dataclass(frozen=True)
class UnmatchedSupplier:
    organisation_id: int
    name: str
    contract_count: int
    total_value: float


def unmatched_supplier_report(session: Session, *, limit: int = 25) -> list[UnmatchedSupplier]:
    """Highest-value suppliers currently mapped to ``other`` (spec 7.3).

    Ranks by summed contract value so the mapping can be improved where it matters
    most. Defence-scoped contracts only — that is the market this product covers.
    """
    from app.models import CompetitorGroup, Contract, Organisation

    stmt = (
        select(
            Organisation.id,
            Organisation.name,
            func.count(Contract.ocid).label("contract_count"),
            func.coalesce(func.sum(Contract.value_amount), 0).label("total_value"),
        )
        .join(Contract, Contract.supplier_org_id == Organisation.id)
        .join(CompetitorGroup, Organisation.competitor_group_id == CompetitorGroup.id)
        .where(CompetitorGroup.slug == DEFAULT_GROUP_SLUG)
        .where(Contract.is_defence.is_(True))
        .group_by(Organisation.id, Organisation.name)
        .order_by(func.coalesce(func.sum(Contract.value_amount), 0).desc())
        .limit(limit)
    )
    return [
        UnmatchedSupplier(
            organisation_id=row.id,
            name=row.name,
            contract_count=int(row.contract_count),
            total_value=float(row.total_value),
        )
        for row in session.execute(stmt).all()
    ]
