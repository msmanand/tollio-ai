from fastapi.testclient import TestClient

from app.data import ntta_matrix
from main import app


client = TestClient(app)


def test_mongodb_strict_mode_does_not_silently_fallback(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mongodb")
    monkeypatch.setenv("MONGODB_URI", "mongodb://test-only")
    monkeypatch.delenv("ALLOW_LOCAL_NTTA_FALLBACK", raising=False)
    monkeypatch.setattr("app.data.ntta_matrix.load_matrix_roads_from_mongodb", lambda: [])

    response = client.get("/api/v1/ntta/roads")

    assert response.status_code == 503
    body = response.json()["detail"]
    assert body["error"] == "ntta_matrix_unavailable"
    assert body["runtime_data_source"] == "mongodb_unavailable"


def test_mongodb_mode_allows_local_fallback_only_when_enabled(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mongodb")
    monkeypatch.setenv("MONGODB_URI", "mongodb://test-only")
    monkeypatch.setenv("ALLOW_LOCAL_NTTA_FALLBACK", "true")
    monkeypatch.setattr("app.data.ntta_matrix.load_matrix_roads_from_mongodb", lambda: [])

    roads = ntta_matrix.load_matrix_roads()

    assert roads
    assert ntta_matrix.matrix_data_source() == "local_json"


def test_optimize_endpoint_returns_error_instead_of_hanging_for_invalid_path(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mock")
    monkeypatch.delenv("MONGODB_URI", raising=False)

    response = client.post(
        "/api/v1/optimize/entry-exit",
        json={
            "from_road": "DNT",
            "from_exit": "Not A Real Exit",
            "to_road": "SH-121",
            "to_exit": "Legacy",
            "payment": "tolltag",
            "traffic_mode": "offpeak",
            "vehicle_type": "gas",
            "mpg": 28,
            "gas_price": 3.25,
        },
    )

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["error"] == "unknown_exit"
    assert "message" in detail
    assert "details" in detail


def test_mongodb_invocation_endpoint_returns_mcp_proof_fields(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mock")
    monkeypatch.delenv("MONGODB_URI", raising=False)

    response = client.get("/api/v1/demo/mongodb-invocation")

    assert response.status_code == 200
    body = response.json()
    assert body["ntta_matrix_collection"] == "ntta_matrices"
    assert body["optimization_memory_collection"] == "optimization_runs"
    assert body["mcp_config_present"] is True
    assert "save_trip_decision_tool" in body["mcp_tools_available"]
    assert body["last_memory_trace"]["tool_name"] == "write_memory_probe"
