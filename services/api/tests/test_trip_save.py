from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_trip_save_endpoint_returns_saved_trip_id(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mock")
    monkeypatch.delenv("MONGODB_URI", raising=False)

    response = client.post(
        "/api/v1/trips/save",
        json={
            "commute_plan_id": "sample-plan",
            "user_label": "Morning commute",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "saved"
    assert body["saved_trip_id"] == "mock-trip-sample-plan"
