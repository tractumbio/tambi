"""Invariant tests for the monthly-report deterministic fact builder.

Runs against the dev database. Asserts the facts are internally consistent and that the
coverage summary agrees with the facts — i.e. every figure is SQL-derived, never guessed.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.db.session import get_session_factory
from app.intelligence.facts import build_coverage, build_facts


def _window() -> tuple[date, date]:
    # A wide, stable window over the loaded 5-year Defence data.
    end = date(2026, 9, 16)
    return end - timedelta(days=180), end


def test_facts_structure_and_invariants() -> None:
    start, end = _window()
    with get_session_factory()() as session:
        f = build_facts(session, start, end)

    # Shape.
    for key in ("window", "spend", "new_awards", "amendments", "expiries",
                "competitor_momentum", "by_theme", "contract_source_cn_ids"):
        assert key in f

    # Movement sections: by_competitor values sum to the section total (SQL consistency).
    for section in ("new_awards", "amendments", "expiries"):
        s = f[section]
        assert s["total_count"] >= 0
        assert s["total_value"] >= 0
        comp_sum = sum(c["value"] for c in s["by_competitor"])
        assert abs(comp_sum - s["total_value"]) < 1.0  # rounding tolerance

    # Accenture share is a proper fraction.
    assert 0.0 <= f["spend"]["accenture_share"] <= 1.0
    assert f["spend"]["accenture_value"] <= f["new_awards"]["total_value"] + 1e-6

    # Sources are CN id strings.
    assert all(isinstance(c, str) for c in f["contract_source_cn_ids"])


def test_coverage_agrees_with_facts() -> None:
    start, end = _window()
    with get_session_factory()() as session:
        f = build_facts(session, start, end)
        c = build_coverage(session, start, end)

    # The two independent SQL paths must report the same movement counts.
    assert c["contracts"]["new_awards"] == f["new_awards"]["total_count"]
    assert c["contracts"]["amendments"] == f["amendments"]["total_count"]
    assert c["contracts"]["expiries"] == f["expiries"]["total_count"]
    assert c["opportunities"]["open_atms"] >= 0
    assert c["media"]["total"] == sum(c["media"]["by_category"].values())
