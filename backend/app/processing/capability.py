"""Capability fingerprint builder and ATM opportunity-scoring engine.

Scores a live ATM against each firm's *actual track record* — the descriptions of the
Defence work they have really delivered. Three signals combine into a 0–100 fit:

  * Capability match (dominant) — TF-IDF cosine similarity between the opportunity's
    title+description and the firm's corpus of past-contract descriptions. This is the
    "have you actually done work like this?" signal and drives most of the score.
  * UNSPSC match — do their prior contracts share this procurement category?
  * Agency relationship — do they have a track record with this specific buyer?

The capability signal is a lightweight bag-of-words embedding: term frequencies per firm,
weighted by inverse-document-frequency across all firms so generic Defence-procurement
words (services, support, management) wash out and distinctive capability words (cloud,
vehicle, engineering, software) carry the signal. Fingerprints are cached 5 min.
"""

from __future__ import annotations

import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

_CACHE: dict = {}
_CACHE_TTL = 300.0  # seconds

# Fraction of a firm's embedding centroid drawn from its curated reference-project
# profile vs its AusTender contract history. Applied identically to every firm so the
# capability comparison stays symmetric — no firm gets a data-richness advantage.
_REFERENCE_WEIGHT = 0.5

# Minimal glue-word stoplist; IDF handles domain-generic terms (services, support…).
_STOP = frozenset({
    "the", "and", "for", "with", "from", "this", "that", "are", "was", "will",
    "per", "via", "our", "その", "all", "any", "not", "under", "over", "into",
    "other", "these", "those", "such", "than", "then", "them", "their", "also",
})

_TOKEN_RE = re.compile(r"[a-z][a-z]{2,}")


def _tokenize(txt: str | None) -> list[str]:
    if not txt:
        return []
    return [w for w in _TOKEN_RE.findall(txt.lower()) if w not in _STOP]


@dataclass
class CapabilityFingerprint:
    slug: str
    label: str
    category: str
    contract_count: int
    total_value: float
    unspsc_segments: Counter[str] = field(default_factory=Counter)  # first 2 chars
    unspsc_families: Counter[str] = field(default_factory=Counter)  # first 4 chars
    agencies: Counter[str] = field(default_factory=Counter)         # normalised name
    term_counts: Counter[str] = field(default_factory=Counter)      # raw description terms
    unique_descriptions: Counter[str] = field(default_factory=Counter)  # description → freq
    reference_descriptions: list[str] = field(default_factory=list)  # curated capability corpus
    tfidf: dict[str, float] = field(default_factory=dict)           # unit-normalised vector
    embedding: list[float] | None = None                           # blended centroid


@dataclass
class ScoreSignals:
    capability: float  # 0–1  (embedding/TF-IDF cosine, primary)
    unspsc: float      # 0–1
    agency: float      # 0–1  — NOT scored; surfaced as a boolean tick only

    @property
    def combined(self) -> float:
        # Agency relationship is deliberately excluded from the score: almost every
        # Defence ATM has a DoD buyer, so it inflated all firms roughly equally without
        # adding real discrimination, and there was no defensible weight for it. It is
        # exposed as ``has_agency_relationship`` (a tick) instead.
        return 0.70 * self.capability + 0.30 * self.unspsc

    @property
    def score(self) -> int:
        return round(self.combined * 100)

    @property
    def has_agency_relationship(self) -> bool:
        return self.agency > 0


def _norm_agency(name: str | None) -> str:
    if not name:
        return ""
    return name.split(" - ")[0].strip().lower()


def _build_all(session: Session) -> dict[str, CapabilityFingerprint]:
    rows = session.execute(text("""
        SELECT
            cg.slug, cg.label, cg.category,
            c.unspsc_code,
            c.description,
            o_b.name AS agency_name,
            COALESCE(c.value_amount, 0) AS value_amount
        FROM contracts c
        JOIN organisations o_s ON c.supplier_org_id = o_s.id
        JOIN competitor_groups cg ON o_s.competitor_group_id = cg.id
        JOIN organisations o_b ON c.buyer_org_id = o_b.id
        WHERE c.is_defence = TRUE AND cg.slug != 'other'
    """)).fetchall()

    fps: dict[str, CapabilityFingerprint] = {}

    for row in rows:
        slug = row.slug
        if slug not in fps:
            fps[slug] = CapabilityFingerprint(
                slug=slug, label=row.label, category=row.category,
                contract_count=0, total_value=0.0,
            )
        fp = fps[slug]
        fp.contract_count += 1
        fp.total_value += float(row.value_amount)

        code = row.unspsc_code or ""
        if len(code) >= 2:
            fp.unspsc_segments[code[:2]] += 1
        if len(code) >= 4:
            fp.unspsc_families[code[:4]] += 1

        norm = _norm_agency(row.agency_name)
        if norm:
            fp.agencies[norm] += 1

        for tok in _tokenize(row.description):
            fp.term_counts[tok] += 1

        desc = (row.description or "").strip()
        if len(desc) >= 4:
            fp.unique_descriptions[desc] += 1

    _load_reference_projects(session, fps)
    _compute_tfidf(fps)
    _build_embeddings(fps)
    return fps


def _load_reference_projects(session: Session, fps: dict[str, CapabilityFingerprint]) -> None:
    """Attach each firm's curated reference-project descriptions (symmetric enrichment).

    Reference text also feeds the TF-IDF term vector so the no-embedding fallback path
    gets the same symmetric enrichment.
    """
    rows = session.execute(text(
        "SELECT firm_slug, title, description FROM reference_projects"
    )).fetchall()
    for row in rows:
        fp = fps.get(row.firm_slug)
        if fp is None:
            continue
        blob = f"{row.title}. {row.description}"
        fp.reference_descriptions.append(blob)
        for tok in _tokenize(blob):
            fp.term_counts[tok] += 1


def _build_embeddings(fps: dict[str, CapabilityFingerprint]) -> None:
    """Attach an embedding centroid to each firm, blending two corpora symmetrically:

      * its AusTender contract descriptions (what it has actually won), and
      * its curated reference-project profile (public capability statements).

    Each sub-corpus is embedded into its own unit centroid, then combined with a fixed
    reference weight identical for every firm — so the enrichment can't hand any single
    firm a data-richness edge. No-op (TF-IDF fallback) when no embedding backend is set.
    """
    from app.processing import embeddings as emb

    if not emb.is_available():
        return

    _MAX_UNIQUE = 80  # cap per firm to bound API volume and centroid noise
    try:
        for fp in fps.values():
            # Contract sub-centroid (frequency-weighted)
            contract_c: list[float] = []
            top = fp.unique_descriptions.most_common(_MAX_UNIQUE)
            if top:
                vecs = emb.embed_texts([d for d, _ in top], input_type="document")
                contract_c = emb.weighted_centroid(vecs, [float(c) for _, c in top])

            # Reference sub-centroid (equal-weighted)
            reference_c: list[float] = []
            if fp.reference_descriptions:
                rvecs = emb.embed_texts(fp.reference_descriptions, input_type="document")
                reference_c = emb.weighted_centroid(rvecs, [1.0] * len(rvecs))

            fp.embedding = _blend_centroids(contract_c, reference_c)
    except Exception:
        for fp in fps.values():
            fp.embedding = None


def _blend_centroids(contract_c: list[float], reference_c: list[float]) -> list[float] | None:
    """Combine the contract and reference centroids with the fixed reference weight."""
    from app.processing.embeddings import weighted_centroid

    if contract_c and reference_c:
        return weighted_centroid(
            [contract_c, reference_c], [1.0 - _REFERENCE_WEIGHT, _REFERENCE_WEIGHT]
        )
    return contract_c or reference_c or None


def _compute_tfidf(fps: dict[str, CapabilityFingerprint]) -> None:
    """Compute per-firm unit-normalised TF-IDF vectors over description terms.

    Document = firm. IDF downweights terms common to many firms (generic procurement
    language) and upweights distinctive capability terms. TF is sublinear (1+log count).
    """
    n_docs = len(fps)
    if n_docs == 0:
        return

    doc_freq: Counter[str] = Counter()
    for fp in fps.values():
        for term in fp.term_counts:
            doc_freq[term] += 1

    idf = {
        term: math.log((1 + n_docs) / (1 + df)) + 1.0
        for term, df in doc_freq.items()
    }

    for fp in fps.values():
        vec: dict[str, float] = {}
        for term, count in fp.term_counts.items():
            tf = 1.0 + math.log(count)
            vec[term] = tf * idf[term]
        norm = math.sqrt(sum(w * w for w in vec.values()))
        if norm > 0:
            fp.tfidf = {t: w / norm for t, w in vec.items()}
        # stash idf on the object graph for ATM-side vectorisation
    # attach shared idf table to the cache (all firms share it)
    _CACHE["idf"] = idf


def get_fingerprints(session: Session) -> dict[str, CapabilityFingerprint]:
    now = time.monotonic()
    if now - _CACHE.get("ts", 0.0) > _CACHE_TTL:
        _CACHE["fps"] = _build_all(session)
        _CACHE["ts"] = now
    return _CACHE["fps"]  # type: ignore[return-value]


def invalidate_cache() -> None:
    _CACHE.clear()


def _atm_vector(title: str | None, description: str | None) -> dict[str, float]:
    """Unit-normalised TF-IDF vector for an ATM using the shared firm-corpus IDF."""
    idf: dict[str, float] = _CACHE.get("idf", {})
    counts = Counter(_tokenize(title) + _tokenize(description))
    if not counts:
        return {}
    vec: dict[str, float] = {}
    for term, count in counts.items():
        # Unknown terms (never seen in any firm corpus) get a neutral high IDF so a
        # genuinely novel word doesn't silently vanish, but they can't match anything.
        weight = idf.get(term)
        if weight is None:
            continue
        vec[term] = (1.0 + math.log(count)) * weight
    norm = math.sqrt(sum(w * w for w in vec.values()))
    if norm == 0:
        return {}
    return {t: w / norm for t, w in vec.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    # iterate the smaller dict
    if len(a) > len(b):
        a, b = b, a
    return sum(w * b.get(t, 0.0) for t, w in a.items())


def score_atm(
    unspsc_code: str | None,
    agency_name: str | None,
    fp: CapabilityFingerprint,
    atm_vec: dict[str, float] | None = None,
    *,
    title: str | None = None,
    description: str | None = None,
    atm_embedding: list[float] | None = None,
) -> ScoreSignals:
    """Score an ATM against one firm's fingerprint.

    Pass a precomputed ``atm_vec`` (TF-IDF) and/or ``atm_embedding`` (Voyage) when scoring
    the same ATM against many firms to avoid recomputation. Embedding cosine is preferred
    when both the ATM and the firm have embeddings; otherwise TF-IDF cosine is used.
    """
    if atm_vec is None:
        atm_vec = _atm_vector(title, description)

    # ── Capability signal — primary. Embedding cosine preferred, TF-IDF fallback ──
    if atm_embedding and fp.embedding:
        from app.processing.embeddings import calibrate_similarity, cosine as _emb_cosine

        cos = _emb_cosine(atm_embedding, fp.embedding)
        capability_s = calibrate_similarity(cos)
    else:
        cos = _cosine(atm_vec, fp.tfidf)
        # Short-text TF-IDF cosines rarely exceed ~0.4; scale so a solid match reads high.
        capability_s = min(1.0, cos * 2.2)

    # ── UNSPSC signal ──────────────────────────────────────────────────────
    unspsc_s = 0.0
    code = unspsc_code or ""
    if code and fp.contract_count > 0:
        seg = code[:2] if len(code) >= 2 else ""
        fam = code[:4] if len(code) >= 4 else ""
        seg_frac = fp.unspsc_segments.get(seg, 0) / fp.contract_count
        fam_frac = fp.unspsc_families.get(fam, 0) / fp.contract_count
        unspsc_s = min(1.0, (seg_frac * 0.30 + fam_frac * 0.70) * 5)

    # ── Agency signal ──────────────────────────────────────────────────────
    agency_s = 0.0
    atm_norm = _norm_agency(agency_name)
    if atm_norm and fp.contract_count > 0:
        count = fp.agencies.get(atm_norm, 0)
        if count == 0:
            for known, cnt in fp.agencies.items():
                if known and (known in atm_norm or atm_norm in known):
                    count = max(count, cnt)
        agency_s = min(1.0, count / 5)

    return ScoreSignals(capability=capability_s, unspsc=unspsc_s, agency=agency_s)


def atm_vector(title: str | None, description: str | None) -> dict[str, float]:
    """Public wrapper — build an ATM's TF-IDF vector once, reuse across firms."""
    return _atm_vector(title, description)


def atm_embedding(title: str | None, description: str | None) -> list[float] | None:
    """Embed an ATM's title+description via Voyage, or None if unavailable."""
    from app.processing import embeddings as emb

    if not emb.is_available():
        return None
    text_parts = [p for p in (title, description) if p]
    if not text_parts:
        return None
    try:
        return emb.embed_one(". ".join(text_parts), input_type="query")
    except Exception:
        return None


def scoring_mode(fps: dict[str, CapabilityFingerprint]) -> str:
    """'embedding' if firm centroids are present, else 'tfidf'."""
    return "embedding" if any(fp.embedding for fp in fps.values()) else "tfidf"


# Thresholds calibrated for the capability+UNSPSC scale (agency excluded). Capability is
# weighted 0.70 so a perfect track-record match tops out ~70; competitors with rich
# contract history reach higher via the UNSPSC component.
def grade(score: int) -> str:
    if score >= 58:
        return "A"
    if score >= 40:
        return "B"
    if score >= 22:
        return "C"
    return "D"


def recommend(score: int) -> str:
    if score >= 52:
        return "pursue"
    if score >= 34:
        return "watch"
    if score >= 18:
        return "monitor"
    return "pass"


def threat_level(max_competitor_score: int) -> str:
    if max_competitor_score >= 62:
        return "high"
    if max_competitor_score >= 45:
        return "medium"
    return "low"
