"""Supplier -> competitor group mapping tests (spec Section 7.3)."""

from __future__ import annotations

import pytest

from app.ingest.transform import normalise_name
from app.processing.competitors import DEFAULT_GROUP_SLUG, map_supplier


@pytest.mark.parametrize(
    ("raw_name", "expected_slug"),
    [
        ("Accenture Australia Holdings Pty Ltd", "accenture"),
        ("Deloitte Touche Tohmatsu", "deloitte"),
        ("PricewaterhouseCoopers Consulting", "pwc"),
        ("KPMG Australia", "kpmg"),
        ("Ernst & Young", "ey"),
        ("IBM Australia Limited", "ibm"),
        ("DXC Technology Australia Pty Ltd", "dxc"),
        ("Leidos Australia Pty Ltd", "leidos"),
        ("Lockheed Martin Australia", "lockheed-martin"),
        ("BAE Systems Australia", "bae-systems"),
        ("Thales Australia Limited", "thales"),
        ("Boeing Defence Australia", "boeing-defence"),
        ("Babcock Pty Ltd", "babcock"),
        ("Nova Systems Pty Ltd", "nova-systems"),
    ],
)
def test_known_competitors_map(raw_name: str, expected_slug: str) -> None:
    assert map_supplier(normalise_name(raw_name), None) == expected_slug


def test_unmatched_falls_to_other() -> None:
    assert map_supplier(normalise_name("Whizdom Pty Ltd"), None) == DEFAULT_GROUP_SLUG


def test_short_token_no_substring_collision() -> None:
    # "ey" is a token rule, so it must not fire inside an unrelated word like "Honeywell".
    assert map_supplier(normalise_name("Honeywell Limited"), None) == DEFAULT_GROUP_SLUG
    # "bae" token must not fire inside "Baesler".
    assert map_supplier(normalise_name("Baesler Trading Co"), None) == DEFAULT_GROUP_SLUG


def test_abn_takes_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    # An ABN match should resolve even when the name would otherwise fall to 'other'.
    import app.processing.competitors as comp

    real = comp._load_rules()
    patched = tuple(
        r if r.slug != "accenture" else comp._GroupRule(
            slug="accenture",
            abns=frozenset({"49096776895"}),
            name_tokens=r.name_tokens,
            name_contains=r.name_contains,
        )
        for r in real
    )
    monkeypatch.setattr(comp, "_load_rules", lambda: patched)
    assert comp.map_supplier(normalise_name("Some Reseller Pty Ltd"), "49 096 776 895") == "accenture"
