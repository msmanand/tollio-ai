from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


READINESS_ENV = [
    "GOOGLE_MAPS_API_KEY",
    "ENABLE_LIVE_ROUTES",
    "MONGODB_URI",
    "TOLLIO_STORAGE_MODE",
    "GEMINI_API_KEY",
    "TOLLIO_AGENT_MODE",
]


def _clear_readiness_env(monkeypatch):
    for name in READINESS_ENV:
        monkeypatch.delenv(name, raising=False)


def test_system_status_mock_mode_works_with_no_credentials(monkeypatch):
    _clear_readiness_env(monkeypatch)

    response = client.get("/api/v1/system/status")

    assert response.status_code == 200
    body = response.json()
    assert body["api_status"] == "ok"
    assert body["routes_mode"] == "mock"
    assert body["mongodb_mode"] == "mock"
    assert body["agent_mode"] == "mock"
    assert body["warnings"] == []


def test_readiness_flags_false_when_env_vars_missing(monkeypatch):
    _clear_readiness_env(monkeypatch)
    monkeypatch.setenv("ENABLE_LIVE_ROUTES", "true")
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mongodb")
    monkeypatch.setenv("TOLLIO_AGENT_MODE", "live")

    body = client.get("/api/v1/system/status").json()

    assert body["google_routes_ready"] is False
    assert body["mongodb_ready"] is False
    assert body["gemini_ready"] is False
    assert len(body["warnings"]) == 3


def test_readiness_flags_true_when_env_vars_are_injected(monkeypatch):
    _clear_readiness_env(monkeypatch)
    monkeypatch.setenv("ENABLE_LIVE_ROUTES", "true")
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-google-maps-key")
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mongodb")
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("TOLLIO_AGENT_MODE", "live")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    body = client.get("/api/v1/system/status").json()

    assert body["routes_mode"] == "live"
    assert body["mongodb_mode"] == "live"
    assert body["agent_mode"] == "live"
    assert body["google_routes_ready"] is True
    assert body["mongodb_ready"] is True
    assert body["gemini_ready"] is True
    assert body["warnings"] == []


def test_status_endpoint_returns_expected_schema(monkeypatch):
    _clear_readiness_env(monkeypatch)

    body = client.get("/api/v1/system/status").json()

    assert set(body.keys()) == {
        "api_status",
        "routes_mode",
        "mongodb_mode",
        "agent_mode",
        "google_routes_ready",
        "mongodb_ready",
        "gemini_ready",
        "warnings",
    }
