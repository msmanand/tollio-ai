from fastapi.testclient import TestClient

from app.data import ntta_matrix
from main import app


client = TestClient(app)


class FakeCollection:
    def __init__(self, count=0):
        self.count = count

    def count_documents(self, query):
        return self.count


class FakeDatabase(dict):
    def __getitem__(self, name):
        return super().__getitem__(name)


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
    assert body["last_memory_trace"]["collection"] == "optimization_runs"
    assert body["errors"] == []


def test_mongodb_invocation_endpoint_returns_success_when_mongodb_ready(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mongodb")
    monkeypatch.setenv("MONGODB_URI", "mongodb://test-only")
    fake_db = FakeDatabase({"ntta_matrices": FakeCollection(count=4)})
    monkeypatch.setattr("app.routes.get_database", lambda: fake_db)
    monkeypatch.setattr(
        "app.routes.write_memory_probe",
        lambda: {"status": "success", "data_source": "mongodb", "saved_id": "fake-id"},
    )

    response = client.get("/api/v1/demo/mongodb-invocation")

    assert response.status_code == 200
    body = response.json()
    assert body["mongodb_ready"] is True
    assert body["runtime_data_source"] == "mongodb"
    assert body["seeded_matrix_count"] == 4
    assert body["memory_write_test"]["status"] == "success"
    assert body["status"] == "success"
    assert body["errors"] == []


def test_mongodb_invocation_endpoint_returns_degraded_when_connection_fails(monkeypatch):
    def fail_database():
        raise RuntimeError("sensitive-uri-token")

    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mongodb")
    monkeypatch.setenv("MONGODB_URI", "sensitive-uri-token")
    monkeypatch.setattr("app.routes.get_database", fail_database)
    monkeypatch.setattr(
        "app.routes.write_memory_probe",
        lambda: {"status": "failure", "data_source": "mongodb", "error": "RuntimeError"},
    )

    response = client.get("/api/v1/demo/mongodb-invocation")

    assert response.status_code == 200
    body_text = response.text
    body = response.json()
    assert body["status"] == "degraded"
    assert body["mongodb_ready"] is False
    assert body["errors"][0]["stage"] == "mongodb_connection"
    assert "sensitive-uri-token" not in body_text


def test_mongodb_invocation_endpoint_returns_degraded_when_memory_write_fails(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mongodb")
    monkeypatch.setenv("MONGODB_URI", "mongodb://test-only")
    fake_db = FakeDatabase({"ntta_matrices": FakeCollection(count=4)})
    monkeypatch.setattr("app.routes.get_database", lambda: fake_db)
    monkeypatch.setattr(
        "app.routes.write_memory_probe",
        lambda: {"status": "failure", "data_source": "mongodb", "error": "OperationFailure"},
    )

    response = client.get("/api/v1/demo/mongodb-invocation")

    assert response.status_code == 200
    body = response.json()
    assert body["mongodb_ready"] is True
    assert body["seeded_matrix_count"] == 4
    assert body["memory_write_test"]["status"] == "failure"
    assert body["status"] == "degraded"
    assert body["errors"][0]["stage"] == "memory_write_test"


def test_app_health_does_not_depend_on_mongodb_at_startup(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mongodb")
    monkeypatch.setenv("MONGODB_URI", "mongodb://test-only")
    monkeypatch.setattr("app.routes.get_database", lambda: (_ for _ in ()).throw(RuntimeError("down")))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
