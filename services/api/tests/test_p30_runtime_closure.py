from fastapi.testclient import TestClient
import sys
from pathlib import Path

from app.data import ntta_matrix
from app.persistence.optimization_repository import save_optimization_run
from main import app

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
from scripts import seed_ntta_to_mongodb


client = TestClient(app)


class FakeCursor(list):
    def sort(self, *args):
        return self

    def limit(self, count):
        return FakeCursor(self[:count])


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []
        self.inserted = []

    def find(self, *args, **kwargs):
        return FakeCursor(self.docs)

    def insert_one(self, document):
        self.inserted.append(document)

        class Result:
            inserted_id = "fake-insert-id"

        return Result()


class FakeDatabase(dict):
    def __getitem__(self, name):
        return super().__getitem__(name)


def test_seed_script_skips_without_mongodb_uri(monkeypatch, capsys):
    monkeypatch.delenv("MONGODB_URI", raising=False)

    assert seed_ntta_to_mongodb.main() == 0
    assert "seed skipped" in capsys.readouterr().out.lower()


def test_mongo_loader_reads_roads_from_fake_mongo(monkeypatch):
    local_road = ntta_matrix.load_matrix_roads_from_json()[0]
    fake_db = FakeDatabase(
        {
            "ntta_matrices": FakeCollection(
                [
                    {
                        "road_id": local_road.road_id,
                        "road_short": local_road.road_short,
                        "road_name": local_road.road_name,
                        "exits": local_road.exits,
                        "tolltag": local_road.tolltag,
                        "zipcash": local_road.zipcash,
                        "source_file": "MongoDB ntta_matrices",
                        "effective_date": local_road.effective_date,
                        "confidence": "exact",
                    }
                ]
            )
        }
    )

    roads = ntta_matrix.load_matrix_roads_from_mongodb(fake_db)

    assert roads[0].road_short == local_road.road_short
    assert roads[0].source_file == "MongoDB ntta_matrices"


def test_matrix_loader_falls_back_to_local_json_in_mock_mode(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mock")
    monkeypatch.delenv("MONGODB_URI", raising=False)

    roads = ntta_matrix.load_matrix_roads()

    assert roads
    assert ntta_matrix.matrix_data_source() == "local_json"


def test_optimization_memory_writes_in_mongodb_mode(monkeypatch):
    collection = FakeCollection()
    fake_db = FakeDatabase({"optimization_runs": collection})
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mongodb")
    monkeypatch.setenv("MONGODB_URI", "mongodb://test-only")
    monkeypatch.setattr("app.persistence.optimization_repository.get_database", lambda: fake_db)

    result = save_optimization_run(
        {"from_road": "DNT", "payment": "tolltag"},
        {"label": "Best Value Route", "entry": "A", "exit": "B"},
        [{"label": "Natural Route", "entry": "A", "exit": "C"}],
        {"data_source": "mongodb"},
    )

    assert result["status"] == "saved"
    assert result["data_source"] == "mongodb"
    assert collection.inserted[0]["input"]["from_road"] == "DNT"
    assert collection.inserted[0]["best_recommendation"]["label"] == "Best Value Route"


def test_demo_mongodb_invocation_endpoint_returns_expected_fields(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mock")
    monkeypatch.delenv("MONGODB_URI", raising=False)

    response = client.get("/api/v1/demo/mongodb-invocation")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "mongodb_mode",
        "mongodb_ready",
        "ntta_source",
        "collections_checked",
        "sample_road_count",
        "memory_write_test",
        "status",
    }
    assert "ntta_matrices" in body["collections_checked"]
    assert "optimization_runs" in body["collections_checked"]


def test_gemini_live_path_preserves_deterministic_result(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return (
                b'{"candidates":[{"content":{"parts":[{"text":"'
                b'{\\"short_explanation\\":\\"Use the deterministic Tollio recommendation.\\",'
                b'\\"detailed_explanation\\":\\"Do not change prices or routes.\\",'
                b'\\"driver_friendly_summary\\":\\"Follow the provided entry and exit.\\",'
                b'\\"caution_notes\\":[\\"Gemini explains only\\"]}'
                b'"}]}}]}'
            )

    monkeypatch.setenv("TOLLIO_AGENT_MODE", "live")
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    monkeypatch.setattr(
        "app.services.explanation_service.urllib_request.urlopen",
        lambda req, timeout: FakeResponse(),
    )

    response = client.get("/api/v1/demo/gemini-invocation")

    assert response.status_code == 200
    body = response.json()
    assert body["invocation_path"]["gemini_invoked"] is True
    assert body["sample_explanation"]["short_explanation"] == "Use the deterministic Tollio recommendation."
