"""Tests for the FastAPI API endpoints (using TestClient, no DB)."""

from fastapi.testclient import TestClient

from hanke_radar.api.app import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "hanke-radar"
