from fastapi.testclient import TestClient

from app.data import ntta_matrix
from main import app


client = TestClient(app)


class FakeCursor(list):
    def sort(self, *args):
        return self


class FakeCollection:
    def __init__(self, docs):
        self.docs = docs

    def find(self, *args, **kwargs):
        return FakeCursor(self.docs)


class FakeDatabase(dict):
    def __getitem__(self, name):
        return super().__getitem__(name)


def _fake_mongo_db():
    local_road = ntta_matrix.load_matrix_roads_from_json()[0]
    return FakeDatabase(
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
                        "source_metadata": {
                            "source_file": local_road.source_file,
                            "effective_date": local_road.effective_date,
                            "confidence": local_road.confidence,
                        },
                    }
                ]
            )
        }
    )


def test_mongodb_mode_response_includes_runtime_source_from_fake_mongo(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mongodb")
    monkeypatch.setenv("MONGODB_URI", "mongodb://test-only")
    monkeypatch.setattr("app.data.ntta_matrix.get_database", _fake_mongo_db)

    response = client.get("/api/v1/ntta/roads")

    assert response.status_code == 200
    body = response.json()
    assert body["source_metadata"]["runtime_data_source"] == "mongodb"
    assert body["source_metadata"]["original_rate_source"] == "NTTAS Toll Calculator_April 2025.pdf"
    assert body["source_metadata"]["source_confidence"] == "uploaded_pdf_matrix_transcription"
    assert body["roads"][0]["runtime_data_source"] == "mongodb"
    assert body["roads"][0]["original_rate_source"] == "NTTAS Toll Calculator_April 2025.pdf"


def test_mock_mode_response_includes_local_json_runtime_source(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mock")
    monkeypatch.delenv("MONGODB_URI", raising=False)

    response = client.get("/api/v1/ntta/price", params={
        "road": "DNT",
        "from_exit": "Walnut Hill/Royal",
        "to_exit": "Trinity Mills/Frankford",
    })

    assert response.status_code == 200
    body = response.json()
    assert body["runtime_data_source"] == "local_json"
    assert body["original_rate_source"] == "NTTAS Toll Calculator_April 2025.pdf"
    assert body["effective_date"] == "2025-04-01"
    assert body["source_confidence"] == "uploaded_pdf_matrix_transcription"
