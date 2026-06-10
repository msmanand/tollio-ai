from fastapi.testclient import TestClient

from app.models import BudgetPeriod, UrgencyMode
from app.services.budget_engine import evaluate_budget
from main import app


client = TestClient(app)


def test_daily_budget_under_budget():
    result = evaluate_budget(
        budget_amount=8.0,
        budget_period=BudgetPeriod.daily,
        current_period_spend=2.0,
        commute_days_per_week=5,
        trips_per_commute_day=2,
        include_weekends=False,
        planned_trip_toll_cost=3.0,
        urgency_mode=UrgencyMode.balanced,
    )

    assert result.remaining_budget == 6.0
    assert result.estimated_commute_days_remaining == 1
    assert result.estimated_trips_remaining == 2
    assert result.recommended_per_trip_allowance == 3.0
    assert result.after_trip_remaining_budget == 3.0
    assert result.budget_status == "under_budget"
    assert result.forecast_status == "on_track"


def test_weekly_budget_divided_across_commute_days():
    result = evaluate_budget(
        budget_amount=50.0,
        budget_period=BudgetPeriod.weekly,
        current_period_spend=10.0,
        commute_days_per_week=5,
        trips_per_commute_day=2,
        include_weekends=False,
        planned_trip_toll_cost=3.5,
        urgency_mode=UrgencyMode.saver,
    )

    assert result.estimated_commute_days_remaining == 5
    assert result.estimated_trips_remaining == 10
    assert result.recommended_per_trip_allowance == 4.0
    assert result.forecast_status == "on_track"


def test_monthly_budget_excludes_weekends_from_remaining_days():
    result = evaluate_budget(
        budget_amount=200.0,
        budget_period=BudgetPeriod.monthly,
        current_period_spend=20.0,
        commute_days_per_week=5,
        trips_per_commute_day=2,
        include_weekends=False,
        remaining_days_in_period=14,
        planned_trip_toll_cost=8.0,
        urgency_mode=UrgencyMode.balanced,
    )

    assert result.estimated_commute_days_remaining == 10
    assert result.estimated_trips_remaining == 20
    assert result.recommended_per_trip_allowance == 9.0


def test_yearly_budget_creates_per_trip_allowance():
    result = evaluate_budget(
        budget_amount=2400.0,
        budget_period=BudgetPeriod.yearly,
        current_period_spend=400.0,
        commute_days_per_week=5,
        trips_per_commute_day=2,
        include_weekends=False,
        planned_trip_toll_cost=3.0,
        urgency_mode=UrgencyMode.balanced,
    )

    assert result.estimated_commute_days_remaining == 260
    assert result.estimated_trips_remaining == 520
    assert result.recommended_per_trip_allowance == 3.85
    assert result.forecast_status == "on_track"


def test_over_budget_user_gets_stronger_avoidance_recommendation():
    result = evaluate_budget(
        budget_amount=8.0,
        budget_period=BudgetPeriod.daily,
        current_period_spend=9.0,
        commute_days_per_week=5,
        trips_per_commute_day=2,
        include_weekends=False,
        planned_trip_toll_cost=1.0,
        urgency_mode=UrgencyMode.saver,
    )

    assert result.budget_status == "over_budget"
    assert result.forecast_status == "projected_over"
    assert "stronger toll avoidance" in result.recommendation


def test_commute_plan_includes_dashboard_ready_budget_summary():
    response = client.post(
        "/api/v1/commute/plan",
        json={
            "origin": "Frisco",
            "destination": "Downtown Dallas",
            "arrival_time": "08:30",
            "urgency_mode": "balanced",
            "daily_budget": 8,
            "weekly_budget": 40,
            "monthly_budget": 160,
            "budget_period": "daily",
            "toll_pass_type": "NTTA TollTag",
            "vehicle_mpg": 28,
            "gas_price": 3.25,
            "avoid_excessive_signals": True,
            "current_period_spend": 1.25,
            "commute_days_per_week": 5,
            "trips_per_commute_day": 2,
            "include_weekends": False,
        },
    )

    assert response.status_code == 200
    budget_summary = response.json()["budget_summary"]
    assert budget_summary["spend_to_date"] == 1.25
    assert "budget_remaining" in budget_summary
    assert "projected_period_spend" in budget_summary
    assert "projected_overage" in budget_summary
    assert "savings_to_date" in budget_summary
    assert "dashboard_message" in budget_summary


def test_budget_status_endpoint_includes_budget_summary():
    response = client.get("/api/v1/budget/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {
        "budget_available",
        "budget_exceeded",
        "under_budget",
        "close_to_limit",
        "over_budget",
    }
    assert body["budget_summary"]["spend_to_date"] == body["estimated_spend"]
    assert "dashboard_message" in body["budget_summary"]
