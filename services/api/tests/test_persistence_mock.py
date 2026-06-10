from app.persistence.budget_repository import BudgetRepository
from app.persistence.mongodb_client import should_use_mongodb
from app.persistence.trip_repository import TripRepository


def test_mock_mode_works_without_mongodb_uri(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mock")
    monkeypatch.delenv("MONGODB_URI", raising=False)

    assert should_use_mongodb() is False

    trip_repository = TripRepository()
    budget_repository = BudgetRepository()

    saved = trip_repository.save_trip_decision(
        commute_plan_id="sample-plan",
        user_label="Morning commute",
        estimated_savings=4.5,
        optimized_route_cost=6.25,
    )
    budget = budget_repository.get_budget_status()

    assert saved.saved_trip_id == "trip-sample-plan"
    assert trip_repository.get_recent_trips().data_source == "mock_persistence"
    assert trip_repository.get_savings_summary().estimated_total_savings >= 4.5
    assert budget.status == "budget_available"
    assert budget.data_source == "mock_persistence"


def test_update_budget_profile_in_mock_mode(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mock")
    monkeypatch.delenv("MONGODB_URI", raising=False)

    repository = BudgetRepository()
    updated = repository.update_budget_profile(
        user_id="demo-user",
        daily_budget=12.0,
        weekly_budget=60.0,
        monthly_budget=240.0,
    )

    assert updated.daily_budget == 12.0
    assert repository.get_budget_status(user_id="demo-user").budget_limit == 12.0
