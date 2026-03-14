"""Tests for API endpoints."""
import os
import pytest

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic.db")


@pytest.fixture(scope="module")
def client():
    if not os.path.exists(DB_PATH):
        pytest.skip("synthetic.db not found — run scripts/generate_data.py first")

    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["nodes"] > 0


def test_recommendations(client):
    resp = client.post("/api/recommendations", json={
        "task_id": "T-2025-0001",
        "priority": "high",
        "destination_uwi": "05-0000-001",
        "planned_start": "2025-02-20T08:00:00",
        "planned_duration_hours": 4.5,
    })
    # Could be 200 or 404 depending on data
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "units" in data
        for unit in data["units"]:
            assert "wialon_id" in unit
            assert "distance_km" in unit
            assert "score" in unit


def test_route(client):
    resp = client.post("/api/route", json={
        "from": {"lon": 68.1, "lat": 51.6},
        "to": {"lon": 68.3, "lat": 51.8},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["distance_km"] > 0
    assert "nodes" in data
    assert len(data["coords"]) > 0


def test_multitask(client):
    resp = client.post("/api/multitask", json={
        "task_ids": ["T-2025-0001", "T-2025-0002", "T-2025-0003"],
        "constraints": {"max_detour_ratio": 1.5},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "groups" in data
    assert "savings_percent" in data
    assert "strategy_summary" in data
    assert "total_distance_km" in data


def test_viz(client):
    resp = client.get("/api/viz/route")
    assert resp.status_code == 200
    assert "html" in resp.headers["content-type"].lower()
