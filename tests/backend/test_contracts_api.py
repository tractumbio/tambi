"""Structural tests for the contract data endpoints (spec Phase 5)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_contracts_list_pagination(client: TestClient) -> None:
    r = client.get("/api/v1/contracts", params={"limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert {"items", "total", "limit", "offset"} <= body.keys()
    assert len(body["items"]) <= 5
    assert body["limit"] == 5


def test_contracts_list_sort_desc_by_value(client: TestClient) -> None:
    r = client.get("/api/v1/contracts", params={"limit": 10, "sort": "value_amount", "order": "desc"})
    assert r.status_code == 200
    values = [i["value_amount"] for i in r.json()["items"] if i["value_amount"] is not None]
    assert values == sorted(values, reverse=True)


def test_contracts_list_rejects_bad_order(client: TestClient) -> None:
    assert client.get("/api/v1/contracts", params={"order": "sideways"}).status_code == 422


def test_contract_detail_and_404(client: TestClient) -> None:
    first = client.get("/api/v1/contracts", params={"limit": 1}).json()["items"]
    if first:
        ocid = first[0]["ocid"]
        detail = client.get(f"/api/v1/contracts/{ocid}")
        assert detail.status_code == 200
        body = detail.json()
        assert body["ocid"] == ocid
        assert isinstance(body["releases"], list)
        # amendment_count should reconcile with the number of archived releases.
        assert len(body["releases"]) >= body["amendment_count"]
    assert client.get("/api/v1/contracts/does-not-exist").status_code == 404


def test_filters_options(client: TestClient) -> None:
    r = client.get("/api/v1/filters")
    assert r.status_code == 200
    body = r.json()
    assert len(body["themes"]) == 5
    assert any(c["slug"] == "accenture" for c in body["competitors"])
    assert {"min", "max"} <= body["value_range"].keys()
