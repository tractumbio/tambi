"""Defence scoping and Tier-1 theme classification (spec Section 7).

Two responsibilities, both deliberately explicit and auditable rather than a black
box — an MD will eventually ask *why* a contract is in or out of scope, or why it
carries a theme, and the answer has to be inspectable:

1. ``score_defence`` — decides ``contracts.is_defence`` by combining three signals
   (buyer portfolio, UNSPSC range, keywords) and returns the reasons that fired.
2. ``classify_themes`` — Tier-1 deterministic keyword/UNSPSC classification from
   ``theme_rules.yaml``. Contracts left unclassified (and above a value threshold)
   are the only ones a later Tier-2 LLM pass needs to look at.

Pure functions over :class:`app.ingest.transform.ParsedContract`; no DB, no I/O
beyond loading the YAML rule file once. Unit-testable against the saved sample.
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.ingest.transform import ParsedContract, normalise_name

_RULES_PATH = Path(__file__).with_name("theme_rules.yaml")


# --- Defence scoping rule set (spec 7.1) -----------------------------------
# Kept here, in code and explicit, rather than in YAML: these determine whether a
# contract appears at all, so they are the rules most likely to be challenged.

# Buyer organisations in the Defence portfolio. Matched against the normalised
# buyer name (see transform.normalise_name), so suffixes/punctuation are already
# stripped. Values here are likewise normalised.
DEFENCE_BUYER_NORMALISED: frozenset[str] = frozenset(
    normalise_name(n)
    for n in (
        "Department of Defence",
        "Defence",
        "Australian Signals Directorate",
        "Defence Science and Technology Group",
        "Defence Science and Technology Organisation",
        "Capability Acquisition and Sustainment Group",
        "Australian Submarine Agency",
        "Australian Naval Infrastructure",
        "ASC Pty Ltd",
        "Defence Housing Australia",
        "Defence and Veterans' Service Commission",
        "Royal Australian Navy",
        "Royal Australian Air Force",
        "Australian Army",
    )
)

# UNSPSC segment/family prefixes that are defence-relevant on their own. "46" is
# the UNSPSC segment "Defense and Law Enforcement and Security and Safety
# Equipment and Supplies"; "251317" is military watercraft.
DEFENCE_UNSPSC_PREFIXES: tuple[str, ...] = ("46", "251317", "2511", "251015")

# Keyword signals in title/description. Whole-word matched, case-insensitive.
DEFENCE_KEYWORDS: tuple[str, ...] = (
    "defence",
    "military",
    "adf",
    "warfare",
    "warfighter",
    "munition",
    "munitions",
    "weapon",
    "weapons",
    "combat",
    "naval",
    "garrison",
    "barracks",
    "aukus",
    "submarine",
    "frigate",
    "sovereign capability",
)


@dataclass(frozen=True)
class DefenceScoping:
    """Outcome of defence scoping, carrying the reasons that fired for audit."""

    is_defence: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ThemeMatch:
    """A Tier-1 theme classification with its provenance."""

    theme_slug: str
    confidence: float
    method: str  # "keyword" | "unspsc"
    evidence: str  # the specific keyword or code prefix that matched


@functools.lru_cache(maxsize=1)
def _load_rules() -> dict[str, Any]:
    with _RULES_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@functools.lru_cache(maxsize=1)
def _compiled_keyword_patterns() -> dict[str, list[tuple[re.Pattern[str], str]]]:
    """Per-theme compiled whole-word keyword patterns, keyed by theme slug."""
    rules = _load_rules()
    out: dict[str, list[tuple[re.Pattern[str], str]]] = {}
    for slug, spec in rules["themes"].items():
        out[slug] = [(_phrase_pattern(kw), kw) for kw in spec.get("keywords", [])]
    return out


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    """Whole-word, case-insensitive matcher tolerating variable inner whitespace."""
    tokens = [re.escape(tok) for tok in phrase.lower().split()]
    body = r"\s+".join(tokens)
    return re.compile(rf"(?<![a-z0-9]){body}(?![a-z0-9])", re.IGNORECASE)


def _haystack(parsed: ParsedContract) -> str:
    return f"{parsed.title or ''}\n{parsed.description or ''}"


# --- Defence scoping --------------------------------------------------------


def score_defence(parsed: ParsedContract) -> DefenceScoping:
    """Decide ``is_defence`` from buyer, UNSPSC and keyword signals.

    Any single signal is sufficient. All firing reasons are returned so the
    decision can be explained; the loader logs them.
    """
    reasons: list[str] = []

    buyer_norm = parsed.buyer.name_normalised if parsed.buyer else ""
    if buyer_norm and buyer_norm in DEFENCE_BUYER_NORMALISED:
        reasons.append(f"buyer:{buyer_norm}")
    elif buyer_norm and "defence" in buyer_norm.split():
        # Catch portfolio bodies not in the explicit list without matching, e.g.
        # unrelated departments — the explicit set stays the primary control.
        reasons.append(f"buyer_token:{buyer_norm}")

    code = parsed.unspsc_code or ""
    for prefix in DEFENCE_UNSPSC_PREFIXES:
        if code.startswith(prefix):
            reasons.append(f"unspsc:{prefix}")
            break

    text = _haystack(parsed)
    for kw in DEFENCE_KEYWORDS:
        if _phrase_pattern(kw).search(text):
            reasons.append(f"keyword:{kw}")
            break

    return DefenceScoping(is_defence=bool(reasons), reasons=tuple(reasons))


# --- Tier-1 theme classification -------------------------------------------


def classify_themes(parsed: ParsedContract) -> list[ThemeMatch]:
    """Return every Tier-1 theme the contract matches (may be empty or multiple).

    UNSPSC evidence outranks keyword evidence for the same theme; only the single
    strongest match per theme is returned.
    """
    rules = _load_rules()
    conf = rules["confidence"]
    text = _haystack(parsed)
    code = parsed.unspsc_code or ""
    matches: list[ThemeMatch] = []

    for slug, spec in rules["themes"].items():
        unspsc_hit: str | None = None
        for prefix in spec.get("unspsc_prefix", []):
            if code.startswith(str(prefix)):
                unspsc_hit = str(prefix)
                break
        if unspsc_hit is not None:
            matches.append(
                ThemeMatch(slug, float(conf["unspsc"]), "unspsc", f"unspsc:{unspsc_hit}")
            )
            continue

        keyword_hit: str | None = None
        for pattern, kw in _compiled_keyword_patterns()[slug]:
            if pattern.search(text):
                keyword_hit = kw
                break
        if keyword_hit is not None:
            matches.append(
                ThemeMatch(slug, float(conf["keyword"]), "keyword", f"keyword:{keyword_hit}")
            )

    return matches
