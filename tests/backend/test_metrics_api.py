"""Structural tests for the dashboard metric endpoints (spec Phase 5).

These run against the dev database (which the backfill populates), so they assert
shape and invariants rather than exact figures, which change as data loads.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

BASE = "/api/v1/metrics"


def test_summary_shape_and_invariants(client: TestClient) -> None:
    r = client.get(f"{BASE}/summary")
    assert r.status_code == 200
    body = r.json()
    for key in (
        "total_value",
        "contract_count",
        "accenture_value",
        "accenture_share",
        "period_start",
        "period_end",
    ):
        assert key in body
    assert 0.0 <= body["accenture_share"] <= 1.0
    assert body["accenture_value"] <= body["total_value"] + 1e-6


def test_share_over_time_granularity(client: TestClient) -> None:
    r = client.get(f"{BASE}/share-over-time", params={"granularity": "quarter"})
    assert r.status_code == 200
    body = r.json()
    assert body["granularity"] == "quarter"
    assert isinstance(body["points"], list)
    if body["points"]:
        p = body["points"][0]
        assert {"bucket", "competitor_slug", "competitor_label", "value"} <= p.keys()


def test_share_over_time_rejects_bad_granularity(client: TestClient) -> None:
    assert client.get(f"{BASE}/share-over-time", params={"granularity": "weekly"}).status_code == 422


def test_by_theme_returns_all_five_themes(client: TestClient) -> None:
    r = client.get(f"{BASE}/by-theme")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 5
    for row in rows:
        # field + accenture must reconcile to total.
        assert abs(row["field_value"] + row["accenture_value"] - row["total_value"]) < 1.0


def test_competitor_momentum_trend_values(client: TestClient) -> None:
    r = client.get(f"{BASE}/competitor-momentum")
    assert r.status_code == 200
    for row in r.json():
        assert row["trend"] in {"up", "down", "flat"}


def test_expiring_sorted_by_value_desc(client: TestClient) -> None:
    r = client.get(f"{BASE}/expiring", params={"within_days": 365, "limit": 20})
    assert r.status_code == 200
    values = [row["value"] for row in r.json() if row["value"] is not None]
    assert values == sorted(values, reverse=True)


def test_by_agency(client: TestClient) -> None:
    r = client.get(f"{BASE}/by-agency", params={"limit": 5})
    assert r.status_code == 200
    assert len(r.json()) <= 5


VALID_OFFERINGS = {
    "Strategy, Transformation & Advisory",
    "SI & Engineering",
    "Cloud Infrastructure & Cyber",
    "Managed Services & Operations",
    "Data, AI & Automation",
}


def test_service_offerings(client: TestClient) -> None:
    r = client.get(f"{BASE}/service-offerings")
    assert r.status_code == 200
    for row in r.json():
        assert row["service_offering"] in VALID_OFFERINGS
        assert abs(row["field_value"] + row["accenture_value"] - row["total_value"]) < 1.0


def test_service_offerings_fy_window_validation(client: TestClient) -> None:
    assert client.get(f"{BASE}/service-offerings", params={"fy_window": "all"}).status_code == 200
    assert client.get(f"{BASE}/service-offerings", params={"fy_window": "decade"}).status_code == 422


def test_addressable_summary_invariants(client: TestClient) -> None:
    body = client.get(f"{BASE}/addressable-summary").json()
    assert 0.0 <= body["addressable_pct_of_defence"] <= 1.0
    assert 0.0 <= body["accenture_share_of_addressable"] <= 1.0
    assert body["addressable_value"] <= body["total_defence_value"] + 1.0


def test_growth_series_ordered_and_labelled(client: TestClient) -> None:
    body = client.get(f"{BASE}/growth").json()
    years = [p["fy_end_year"] for p in body["points"]]
    assert years == sorted(years)
    for p in body["points"]:
        assert p["fy_label"].startswith("FY")


def test_peer_comparison_cohorts(client: TestClient) -> None:
    for cohort in ("big4", "mbb", "challengers"):
        r = client.get(f"{BASE}/peer-comparison", params={"cohort": cohort})
        assert r.status_code == 200
        body = r.json()
        assert body["cohort"] == cohort
        assert 0.0 <= body["accenture_share"] <= 1.0
        assert sum(m["value"] for m in body["members"]) <= body["cohort_value"] + 1.0
        assert all("accenture" not in m["slug"] for m in body["members"])


def test_peer_comparison_rejects_unknown_cohort(client: TestClient) -> None:
    assert client.get(f"{BASE}/peer-comparison", params={"cohort": "tier1"}).status_code == 422


def test_network_graph_shape(client: TestClient) -> None:
    r = client.get(f"{BASE}/network", params={"agency_limit": 10})
    assert r.status_code == 200
    body = r.json()
    node_ids = {n["id"] for n in body["nodes"]}
    kinds = {n["kind"] for n in body["nodes"]}
    assert kinds <= {"competitor", "agency", "branch", "theme"}
    # no 'other' bucket among competitor nodes
    assert all(n["slug"] != "other" for n in body["nodes"] if n["kind"] == "competitor")
    # hubs must be Defence-portfolio only — never other departments
    hubs = [n["label"].lower() for n in body["nodes"] if n["kind"] in {"agency", "branch"}]
    for bad in ("foreign affairs", "federal police", "health", "agriculture", "climate", "treasury"):
        assert not any(bad in h for h in hubs)
    # every edge connects two present nodes
    for e in body["edges"]:
        assert e["source"] in node_ids and e["target"] in node_ids
