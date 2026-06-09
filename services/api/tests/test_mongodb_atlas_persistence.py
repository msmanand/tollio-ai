import pytest
from fastapi.testclient import TestClient

from app.persistence.budget_repository import BudgetRepository
from app.persistence.mongodb_client import (
    MongoDBConnectionError,
    get_mongodb_client,
    should_use_mongodb,
)
from app.persistence.trip_repository import TripRepository
from main import app


client = TestClient(app)


class FakeCursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, *args):
        return self

    def limit(self, count):
        return self.docs[:count]


class FakeCollection:
    def __init__(self, find_one_doc=None, find_docs=None):
        self.update_calls = []
        self.find_one_calls = []
        self.find_calls = []
        self.find_one_doc = find_one_doc
        self.find_docs = find_docs or []

    def update_one(self, filter_doc, update_doc, upsert=False):
        self.update_calls.append((filter_doc, update_doc, upsert))

    def find_one(self, filter_doc, projection=None):
        self.find_one_calls.append((filter_doc, projection))
        return self.find_one_doc

    def find(self, filter_doc, projection=None):
        self.find_calls.append((filter_doc, projection))
        return FakeCursor(self.find_docs)


class FakeDatabase:
    def __init__(self):
        self.trips = FakeCollection(
            find_docs=[
                {
                    "saved_trip_id": "trip-live-plan",
                    "commute_plan_id": "live-plan",
                    "user_label": "Live commute",
                    "route_summary": "Live route",
                    "estimated_savings": 3.25,
                    "optimized_route_cost": 7.0,
                    "created_by": "tollio_api",
                }
            ]
        )
        self.budgets = FakeCollection(
            find_one_doc={
                "user_id": "demo-user",
                "daily_budget": 9.0,
                "weekly_budget": 45.0,
                "monthly_budget": 180.0,
                "current_daily_spend": 4.0,
                "current_weekly_spend": 12.0,
                "current_monthly_spend": 44.0,
                "data_source": "mongodb",
            }
        )


class FakeAdmin:
    def __init__(self):
        self.commands = []

    def command(self, command_name):
        self.commands.append(command_name)
        return {"ok": 1}


class FakeClient:
    def __init__(self, uri, **kwargs):
        self.uri = uri
        self.kwargs = kwargs
        self.admin = FakeAdmin()
        self.databases = {}

    def __getitem__(self, database_name):
        self.databases.setdefault(database_name, FakeDatabase())
        return self.databases[database_name]


def test_mock_mode_does_not_connect(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mock")
    monkeypatch.delenv("MONGODB_URI", raising=False)

    def fail_client_factory(*args, **kwargs):
        raise AssertionError("MongoDB client should not be created in mock mode")

    assert should_use_mongodb() is False
    assert get_mongodb_client(client_factory=fail_client_factory) is None
    assert TripRepository().data_source == "mock_persistence"


def test_mongodb_mode_requires_uri(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mongodb")
    monkeypatch.delenv("MONGODB_URI", raising=False)

    with pytest.raises(MongoDBConnectionError, match="requires MONGODB_URI"):
        get_mongodb_client(client_factory=FakeClient)


def test_mongodb_client_uses_timeout_and_ping(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mongodb")
    monkeypatch.setenv("MONGODB_URI", "mongodb://example.test:27017")

    client = get_mongodb_client(client_factory=FakeClient)

    assert client.uri == "mongodb://example.test:27017"
    assert client.kwargs["serverSelectionTimeoutMS"] == 2000
    assert client.kwargs["connectTimeoutMS"] == 2000
    assert client.admin.commands == ["ping"]


def test_trip_repository_calls_expected_collection_operations():
    database = FakeDatabase()
    repository = TripRepository(database=database)

    saved = repository.save_trip_decision(
        commute_plan_id="live-plan",
        user_label="Live commute",
        estimated_savings=3.25,
        optimized_route_cost=7.0,
    )
    recent = repository.get_recent_trips()
    summary = repository.get_savings_summary()

    assert saved.saved_trip_id == "trip-live-plan"
    assert database.trips.update_calls[0][2] is True
    assert database.trips.find_calls
    assert recent.trips[0].commute_plan_id == "live-plan"
    assert summary.estimated_total_savings == 3.25


def test_budget_repository_calls_expected_collection_operations():
    database = FakeDatabase()
    repository = BudgetRepository(database=database)

    profile = repository.get_budget_profile()
    updated = repository.update_budget_profile(daily_budget=12.0)
    status = repository.get_budget_status()

    assert profile.daily_budget == 9.0
    assert updated.daily_budget == 12.0
    assert database.budgets.find_one_calls
    assert database.budgets.update_calls[0][2] is True
    assert status.status == "budget_available"


def test_trip_save_endpoint_still_works_in_mock_mode(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mock")
    monkeypatch.delenv("MONGODB_URI", raising=False)

    response = client.post(
        "/api/v1/trips/save",
        json={"commute_plan_id": "sample-plan", "user_label": "Morning commute"},
    )

    assert response.status_code == 200
    assert response.json()["saved_trip_id"] == "trip-sample-plan"


def test_budget_status_endpoint_still_works_in_mock_mode(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mock")
    monkeypatch.delenv("MONGODB_URI", raising=False)

    response = client.get("/api/v1/budget/status")

    assert response.status_code == 200
    assert response.json()["status"] == "budget_available"
