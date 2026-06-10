from fastapi.testclient import TestClient

from app.data.ntta_connections import CONNECTIONS
from app.data.ntta_roads import ROADS
from app.services.value_score import (
    build_value_score_breakdown,
    combined_value_score,
    entry_value_score,
    exit_value_score,
    unused_ahead,
    wasted_behind,
)
from main import app


client = TestClient(app)


def test_ntta_static_data_loads():
    assert "DNT" in ROADS
    assert "SH-121" in ROADS
    assert ROADS["DNT"].exits[17] == "Legacy"
    assert ROADS["SH-121"].exits[17] == "Coit"
    assert any(connection.from_road == "DNT" and connection.to_road == "SH-121" for connection in CONNECTIONS)


def test_value_score_high_when_entry_and_exit_align_with_tier():
    road = ROADS["SH-121"]

    assert entry_value_score(road, 17, 19) == 100
    assert exit_value_score(road, 17, 19) == 100
    assert combined_value_score(road, 17, 19) == 100


def test_value_score_drops_when_entering_after_paid_tier_started():
    road = ROADS["DNT"]

    delayed_score = entry_value_score(road, 15, 0)
    aligned_score = entry_value_score(road, 19, 0)

    assert delayed_score < aligned_score
    assert wasted_behind(road, 15, 0) == 4


def test_unused_ahead_tracks_exits_paid_for_but_not_used():
    road = ROADS["DNT"]

    assert unused_ahead(road, 19, 22) == 1
    assert exit_value_score(road, 19, 22) < 100


def test_delayed_entry_improves_value_score():
    road = ROADS["DNT"]

    too_early = combined_value_score(road, 15, 0)
    better_delayed_entry = combined_value_score(road, 19, 0)

    assert better_delayed_entry > too_early


def test_early_exit_improves_value_score():
    road = ROADS["DNT"]

    exits_before_tier_end = combined_value_score(road, 19, 22)
    uses_full_tier = combined_value_score(road, 19, 23)

    assert uses_full_tier > exits_before_tier_end


def test_breakdown_explains_paid_but_unused_value():
    breakdown = build_value_score_breakdown("DNT", 19, 22)

    assert breakdown is not None
    assert breakdown.unused_ahead == 1
    assert "ahead" in breakdown.paid_but_unused_reason
    assert breakdown.ntta_data_used is True


def test_commute_plan_includes_ntta_value_score_fields():
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
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ntta_data_used"] is True
    assert body["google_routes_data_used"] is False
    assert body["value_score_breakdown"]
    assert body["entry_value_score"] > 0
    assert body["exit_value_score"] > 0
    assert body["combined_value_score"] > 0
    assert "tier" in body["value_loss_reason"].lower()
