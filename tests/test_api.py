"""Tests for API endpoints."""
import os
import sys
import pytest

# Ensure synthetic DB exists before testing
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
        "duration_hours": 4.5,
    })
    # Could be 200 or 404 depending on data
    assert resp.status_code in (200, 404)


def test_route(client):
    resp = client.post("/api/route", json={
        "from_lon": 68.1,
        "from_lat": 51.6,
        "to_lon": 68.3,
        "to_lat": 51.8,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["distance_m"] > 0
    assert len(data["path_coords"]) > 0


def test_viz(client):
    resp = client.get("/api/viz/route")
    assert resp.status_code == 200
    assert "html" in resp.headers["content-type"].lower()
