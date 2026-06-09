from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_budget_status_endpoint_returns_budget_state(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mock")
    monkeypatch.delenv("MONGODB_URI", raising=False)

    response = client.get("/api/v1/budget/status")

    assert response.status_code == 200
    body = response.json()
    assert body["budget_period"] == "daily"
    assert body["budget_limit"] == 8.0
    assert body["remaining_budget"] == 1.75
    assert body["status"] == "budget_available"
