"""Accenture-addressable service-offering classification (spec extension).

Ported from the previous analytics ``build_master.py`` and adapted to the OCDS feed.
The original scored AusTender's ``Category``/``Description``/supplier text into five
service offerings and decided Accenture-addressability. AusTender's OCDS API gives no
``Category Type``/``Category`` text — only a UNSPSC code, title and description — so
the category-text gates are re-expressed as UNSPSC-segment gates while the
description/supplier scoring is ported verbatim (see ``service_offering_rules.yaml``).

Pure functions over the fields we hold on a contract; no DB, no I/O beyond loading the
rules once. The result is auditable: the winning offering carries its score and a
confidence band, mirroring the original.
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_RULES_PATH = Path(__file__).with_name("service_offering_rules.yaml")


@dataclass(frozen=True)
class ServiceClassification:
    is_addressable: bool
    service_offering: str | None
    score: float
    confidence: int  # 0..100, mirrors the original bands
    confidence_band: str  # "Very high" | "High" | "Medium" | "Low"
    reason: str
    evidence: tuple[str, ...] = field(default_factory=tuple)


@functools.lru_cache(maxsize=1)
def _rules() -> dict[str, Any]:
    with _RULES_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def service_offerings() -> list[str]:
    return list(_rules()["service_offerings"])


@functools.lru_cache(maxsize=1)
def _compiled() -> dict[str, Any]:
    r = _rules()
    return {
        "description": {
            offering: [(re.compile(p, re.IGNORECASE), float(w), lbl) for p, w, lbl in rules]
            for offering, rules in r["description_rules"].items()
        },
        "supplier": [
            (re.compile(p, re.IGNORECASE), offering, float(w), lbl)
            for p, offering, w, lbl in r["supplier_hints"]
        ],
        "non_addressable": [re.compile(p, re.IGNORECASE) for p in r["non_addressable_desc"]],
        "strong_rescue": [re.compile(p, re.IGNORECASE) for p in r["strong_addressable_desc"]],
        "hard_goods_segments": frozenset(r["hard_goods_unspsc_segments"]),
        "min_score": float(r["addressable_min_score"]),
    }


def _confidence(winner: float, second: float, sources: int) -> tuple[int, str]:
    """Ported from build_master.confidence_from_scores."""
    margin = winner - second
    if winner <= 0:
        return 25, "Low"
    if winner >= 24 and margin >= 10 and sources >= 2:
        return 97, "Very high"
    if winner >= 18 and margin >= 8:
        return 92, "High"
    if winner >= 13 and margin >= 5:
        return 84, "Medium"
    if winner >= 9 and margin >= 3:
        return 72, "Medium"
    return 50, "Low"


def classify_service_offering(
    *,
    title: str | None,
    description: str | None,
    supplier_name: str | None,
    unspsc_code: str | None,
) -> ServiceClassification:
    """Classify a contract into a service offering and decide addressability."""
    c = _compiled()
    text = f"{title or ''} {description or ''}".strip()
    supplier = supplier_name or ""

    strong_rescue = any(p.search(text) for p in c["strong_rescue"])

    # Hard physical-goods gate (UNSPSC segment) — only a strong digital/service rescue
    # keeps such a contract in scope.
    segment = (unspsc_code or "")[:2]
    if segment in c["hard_goods_segments"] and not strong_rescue:
        return ServiceClassification(
            False, None, 0.0, 100, "Low",
            f"Non-addressable: UNSPSC segment {segment} is physical goods/materiel",
        )

    # Non-addressable subject matter in the text, unless strongly rescued.
    for pat in c["non_addressable"]:
        m = pat.search(text)
        if m and not strong_rescue:
            return ServiceClassification(
                False, None, 0.0, 98, "Low",
                f"Non-addressable: matched '{m.group(0)}'",
            )

    scores = {o: 0.0 for o in service_offerings()}
    evidence: list[str] = []
    for offering, rules in c["description"].items():
        for pattern, weight, label in rules:
            m = pattern.search(text)
            if m:
                scores[offering] += weight
                evidence.append(f"{label}: {m.group(0)} (+{weight:.0f})")
    for pattern, offering, weight, label in c["supplier"]:
        if pattern.search(supplier):
            scores[offering] += weight
            evidence.append(f"{label} (+{weight:.0f})")

    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    winner, winner_score = ordered[0]
    second_score = ordered[1][1] if len(ordered) > 1 else 0.0

    if winner_score < c["min_score"]:
        return ServiceClassification(
            False, None, winner_score, 50, "Low",
            "Non-addressable: no service-offering signal above threshold",
            tuple(evidence),
        )

    sources = sum(1 for _, s in ordered if s > 0)
    conf, band = _confidence(winner_score, second_score, sources)
    return ServiceClassification(
        True, winner, winner_score, conf, band,
        f"Addressable: {winner} (score {winner_score:.0f})",
        tuple(evidence),
    )
