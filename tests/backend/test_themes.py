"""Defence scoping and Tier-1 theme classification tests (spec Section 7)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.ingest.transform import ParsedContract, ParsedParty, normalise_name
from app.processing.themes import classify_themes, score_defence


def _party(name: str, roles: list[str]) -> ParsedParty:
    return ParsedParty(
        source_id=None,
        name=name,
        name_normalised=normalise_name(name),
        abn=None,
        roles=roles,
    )


def _contract(
    *,
    title: str = "",
    description: str = "",
    unspsc_code: str | None = None,
    buyer: str | None = None,
) -> ParsedContract:
    return ParsedContract(
        ocid="ocid-x",
        release_id="rel-x",
        release_date=None,
        tags=["contract"],
        cn_id="CN1",
        title=title,
        description=description,
        value_amount=Decimal("1000"),
        value_currency="AUD",
        date_published=None,
        date_signed=None,
        period_start=date(2026, 1, 1),
        period_end=date(2027, 1, 1),
        procurement_method="open",
        unspsc_code=unspsc_code,
        unspsc_title=None,
        buyer_division=None,
        buyer_branch=None,
        buyer=_party(buyer, ["procuringEntity"]) if buyer else None,
        supplier=None,
    )


# --- Defence scoping --------------------------------------------------------


def test_defence_by_buyer_portfolio() -> None:
    result = score_defence(_contract(buyer="Department of Defence"))
    assert result.is_defence
    assert any(r.startswith("buyer:") for r in result.reasons)


def test_defence_by_unspsc_range() -> None:
    # 46… = UNSPSC Defense/Law Enforcement/Security segment.
    result = score_defence(_contract(unspsc_code="46101500", buyer="Comcare"))
    assert result.is_defence
    assert any(r.startswith("unspsc:") for r in result.reasons)


def test_defence_by_keyword() -> None:
    result = score_defence(_contract(description="Supply of naval munitions", buyer="Comcare"))
    assert result.is_defence
    assert any(r.startswith("keyword:") for r in result.reasons)


def test_non_defence_contract_scoped_out() -> None:
    result = score_defence(
        _contract(
            title="Office cleaning services",
            description="Cleaning of administrative offices",
            unspsc_code="76111500",
            buyer="Department of Social Services",
        )
    )
    assert not result.is_defence
    assert result.reasons == ()


def test_unrelated_department_not_defence_on_buyer_alone() -> None:
    result = score_defence(
        _contract(
            title="Environmental survey",
            buyer="Department of Climate Change, Energy, the Environment and Water",
        )
    )
    assert not result.is_defence


# --- Theme classification ---------------------------------------------------


def test_theme_keyword_match_single() -> None:
    matches = classify_themes(_contract(description="Cyber security operations centre uplift"))
    slugs = {m.theme_slug for m in matches}
    assert "defensive-cyber" in slugs
    cyber = next(m for m in matches if m.theme_slug == "defensive-cyber")
    assert cyber.method == "keyword"
    assert 0 < cyber.confidence <= 1


def test_theme_multiple_matches() -> None:
    matches = classify_themes(
        _contract(description="AUKUS submarine workforce recruitment and skilling programme")
    )
    slugs = {m.theme_slug for m in matches}
    assert {"nuclear-submarines", "workforce"} <= slugs


def test_theme_unspsc_outranks_keyword_confidence() -> None:
    matches = classify_themes(_contract(description="workforce", unspsc_code="801116"))
    workforce = next(m for m in matches if m.theme_slug == "workforce")
    assert workforce.method == "unspsc"


def test_no_theme_when_nothing_matches() -> None:
    assert classify_themes(_contract(description="general office supplies")) == []


def test_keyword_matching_is_whole_word() -> None:
    # "cyber" must not match as a substring of an unrelated word.
    matches = classify_themes(_contract(description="cybernetics research toy"))
    assert all(m.theme_slug != "defensive-cyber" for m in matches)
