"""Transform tests against the real saved sample (spec Section 14: highest-value surface).

A transform bug corrupts everything downstream silently, so this runs against the
actual archived Phase 0 response, not a hand-built fixture.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.ingest.transform import ParsedContract, normalise_name, parse_release

_SAMPLE = Path(__file__).resolve().parents[2] / "data" / "raw" / "sample_response.json"


@pytest.fixture(scope="module")
def releases() -> list[dict]:
    package = json.loads(_SAMPLE.read_text(encoding="utf-8-sig"))
    return package["releases"]


@pytest.fixture(scope="module")
def parsed(releases: list[dict]) -> list[ParsedContract]:
    return [p for r in releases if (p := parse_release(r)) is not None]


def test_sample_has_expected_volume(releases: list[dict]) -> None:
    assert len(releases) == 99


def test_all_releases_parse(parsed: list[ParsedContract], releases: list[dict]) -> None:
    # Every sampled release carries a contracts[] block, so none should drop out.
    assert len(parsed) == len(releases)


def test_value_amount_cast_to_decimal(parsed: list[ParsedContract]) -> None:
    # The feed sends value.amount as a string; the transform must yield Decimal.
    amounts = [p.value_amount for p in parsed if p.value_amount is not None]
    assert amounts, "expected at least one contract with a value"
    assert all(isinstance(a, Decimal) for a in amounts)


def test_cn_id_distinct_from_ocid(parsed: list[ParsedContract]) -> None:
    sample = parsed[0]
    assert sample.cn_id and sample.cn_id.startswith("CN")
    assert sample.ocid and sample.ocid != sample.cn_id


def test_buyer_from_procuring_entity_role(parsed: list[ParsedContract]) -> None:
    with_buyer = [p for p in parsed if p.buyer is not None]
    assert with_buyer
    assert all("procuringEntity" in p.buyer.roles for p in with_buyer)


def test_supplier_from_supplier_role(parsed: list[ParsedContract]) -> None:
    with_supplier = [p for p in parsed if p.supplier is not None]
    assert with_supplier
    assert all("supplier" in p.supplier.roles for p in with_supplier)


def test_unspsc_title_absent_from_feed(parsed: list[ParsedContract]) -> None:
    # Feed carries only the UNSPSC code; title is reference-derived later.
    assert all(p.unspsc_title is None for p in parsed)
    assert any(p.unspsc_code for p in parsed)


def test_release_id_unique(parsed: list[ParsedContract]) -> None:
    ids = [p.release_id for p in parsed]
    assert len(ids) == len(set(ids))


def test_buyer_org_unit_extracted(parsed: list[ParsedContract]) -> None:
    # AusTender exposes the buyer division/branch on a party contactPoint; most rows have it.
    with_unit = [p for p in parsed if p.buyer_division or p.buyer_branch]
    assert with_unit, "expected buyer division/branch to be extracted from the sample"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("SAAB AUSTRALIA PTY LTD", "saab"),
        ("Data #3 Limited", "data 3"),
        ("Accenture Australia Holdings Pty Ltd", "accenture"),
        ("The Boeing Company", "boeing"),
        (None, ""),
    ],
)
def test_normalise_name(raw: str | None, expected: str) -> None:
    assert normalise_name(raw) == expected


def _release_with_period(start: str, end: str) -> dict:
    return {
        "ocid": "ocds-abc-CN123",
        "id": "CN123-1",
        "date": "2024-01-01T00:00:00Z",
        "contracts": [{"id": "CN123", "period": {"startDate": start, "endDate": end}}],
    }


@pytest.mark.parametrize("junk", ["0899-12-28T00:00:00Z", "1900-01-01T00:00:00Z"])
def test_junk_dates_sanitised_to_none(junk: str) -> None:
    # AusTender emits placeholder/corrupt dates — year 0899 and the "1900-01-01"
    # null-sentinel (the bulk of them). Anything below 1990 is treated as missing.
    parsed = parse_release(_release_with_period(junk, junk))
    assert parsed is not None
    assert parsed.period_start is None
    assert parsed.period_end is None


def test_valid_period_dates_kept() -> None:
    parsed = parse_release(
        _release_with_period("2020-07-01T00:00:00Z", "2025-06-30T00:00:00Z")
    )
    assert parsed is not None
    assert parsed.period_start is not None and parsed.period_start.year == 2020
    assert parsed.period_end is not None and parsed.period_end.year == 2025
